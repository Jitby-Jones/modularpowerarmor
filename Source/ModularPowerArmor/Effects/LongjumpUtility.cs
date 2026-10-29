using RimWorld;
using UnityEngine;
using Verse;
using Verse.AI;

namespace ModularPowerArmor
{
    /// <summary>
    /// Longjump hydraulics: the wearer leaps to a cell in range, over walls and through roofs, but
    /// not through mountains (natural rock or overhead mountain) and never onto an occupied cell.
    /// Quality scales the range up and the recharge time down.
    /// </summary>
    public static class LongjumpUtility
    {
        public const int WarmupTicks = 30;

        public static LongjumpProperties PropsFor(Thing module)
        {
            return ArmorModuleUtility.PropsOf(module)?.longjump;
        }

        public static float Range(CompModularArmor armor, Thing module)
        {
            LongjumpProperties props = PropsFor(module);
            return props == null ? 0f : props.range * armor.EffectMultiplier(module);
        }

        public static int CooldownTicks(CompModularArmor armor, Thing module)
        {
            LongjumpProperties props = PropsFor(module);
            return props == null ? 0 : Mathf.RoundToInt(props.cooldownTicks / Mathf.Max(0.1f, armor.EffectMultiplier(module)));
        }

        /// <summary>Whether the pawn can use the hydraulics at all right now (cooldown, overload, state).</summary>
        public static AcceptanceReport CanJumpNow(Pawn pawn, CompModularArmor armor, Thing module)
        {
            if (armor == null || armor.Wearer != pawn || !armor.Modules.Contains(module))
            {
                return false;
            }
            if (armor.IsOverloaded)
            {
                return "MPA_Reason_Overloaded".Translate(armor.parent.LabelShort).Resolve();
            }
            CompArmorModule comp = module.TryGetComp<CompArmorModule>();
            if (comp != null && comp.LongjumpTicksLeft > 0)
            {
                return "MPA_LongjumpRecharging".Translate(comp.LongjumpTicksLeft.ToStringTicksToPeriod()).Resolve();
            }
            if (!pawn.Spawned)
            {
                return false;
            }
            if (pawn.Downed)
            {
                return "MPA_Reason_Downed".Translate(pawn.LabelShort, pawn).Resolve();
            }
            if (pawn.IsBurning())
            {
                return "MPA_Reason_Burning".Translate(pawn.LabelShort, pawn).Resolve();
            }
            return true;
        }

        /// <summary>Whether a leap from the pawn's position can land on <paramref name="cell"/>.</summary>
        public static AcceptanceReport CanJumpTo(Pawn pawn, IntVec3 cell, float range)
        {
            Map map = pawn.Map;
            if (map == null || !cell.IsValid || !cell.InBounds(map) || cell == pawn.Position)
            {
                return false;
            }
            if (cell.Fogged(map))
            {
                return "MPA_LongjumpFogged".Translate().Resolve();
            }
            if (!pawn.Position.InHorDistOf(cell, range))
            {
                return "MPA_LongjumpOutOfRange".Translate().Resolve();
            }
            if (!cell.Standable(map) || cell.GetFirstPawn(map) != null)
            {
                return "MPA_LongjumpOccupied".Translate().Resolve();
            }
            foreach (IntVec3 c in GenSight.PointsOnLineOfSight(pawn.Position, cell))
            {
                if (IsMountain(c, map))
                {
                    return "MPA_LongjumpMountain".Translate().Resolve();
                }
            }
            // PointsOnLineOfSight leaves out both ends.
            if (IsMountain(pawn.Position, map) || IsMountain(cell, map))
            {
                return "MPA_LongjumpMountain".Translate().Resolve();
            }
            return true;
        }

        private static bool IsMountain(IntVec3 cell, Map map)
        {
            if (map.roofGrid.RoofAt(cell)?.isThickRoof == true)
            {
                return true;
            }
            Building edifice = cell.GetEdifice(map);
            return edifice != null && edifice.def.building != null && edifice.def.building.isNaturalRock;
        }

        public static void BeginTargeting(Pawn pawn, CompModularArmor armor, Thing module)
        {
            float range = Range(armor, module);
            TargetingParameters parms = new TargetingParameters
            {
                canTargetLocations = true,
                canTargetSelf = false,
                canTargetPawns = false,
                canTargetBuildings = false,
                canTargetItems = false,
                canTargetFires = false
            };
            Find.Targeter.BeginTargeting(
                parms,
                target => OrderJump(pawn, armor, module, target.Cell),
                target =>
                {
                    if (CanJumpTo(pawn, target.Cell, range).Accepted)
                    {
                        GenDraw.DrawTargetHighlight(target);
                    }
                },
                target => CanJumpTo(pawn, target.Cell, range).Accepted,
                pawn,
                null,
                module.def.uiIcon,
                true,
                target =>
                {
                    AcceptanceReport report = CanJumpTo(pawn, target.Cell, range);
                    if (!report.Accepted && !report.Reason.NullOrEmpty())
                    {
                        Widgets.MouseAttachedLabel(report.Reason);
                    }
                },
                target =>
                {
                    if (pawn.Spawned)
                    {
                        GenDraw.DrawRadiusRing(pawn.Position, range);
                        if (target.IsValid && CanJumpTo(pawn, target.Cell, range).Accepted)
                        {
                            GenDraw.DrawLineBetween(pawn.TrueCenter(), target.CenterVector3);
                        }
                    }
                });
        }

        public static void OrderJump(Pawn pawn, CompModularArmor armor, Thing module, IntVec3 cell)
        {
            if (!CanJumpNow(pawn, armor, module).Accepted || !CanJumpTo(pawn, cell, Range(armor, module)).Accepted)
            {
                return;
            }
            Job job = JobMaker.MakeJob(MPA_DefOf.MPA_Longjump, cell, module);
            pawn.jobs.TryTakeOrderedJob(job, JobTag.Misc);
        }

        /// <summary>Launches the leap and starts the recharge. Returns false if it couldn't happen.</summary>
        public static bool DoJump(Pawn pawn, CompModularArmor armor, Thing module, IntVec3 cell)
        {
            if (!CanJumpNow(pawn, armor, module).Accepted || !CanJumpTo(pawn, cell, Range(armor, module)).Accepted)
            {
                return false;
            }
            CompArmorModule comp = module.TryGetComp<CompArmorModule>();
            int previous = comp?.longjumpReadyTick ?? -1;
            if (comp != null)
            {
                comp.longjumpReadyTick = Find.TickManager.TicksGame + CooldownTicks(armor, module);
            }
            VerbProperties verbProps = new VerbProperties
            {
                flightEffecterDef = DefDatabase<EffecterDef>.GetNamedSilentFail("JumpFlightEffect"),
                soundLanding = DefDatabase<SoundDef>.GetNamedSilentFail("JumpPackLand"),
                flyWithCarriedThing = true
            };
            if (JumpUtility.DoJump(pawn, cell, null, verbProps))
            {
                return true;
            }
            if (comp != null)
            {
                comp.longjumpReadyTick = previous;
            }
            return false;
        }
    }
}
