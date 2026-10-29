using System.Collections.Generic;
using System.Linq;
using System.Text;
using RimWorld;
using UnityEngine;
using Verse;
using Verse.AI;

namespace ModularPowerArmor
{
    public static class ArmorModuleUtility
    {
        private static List<ThingDef> allModuleDefs = new List<ThingDef>();

        public static ModularPowerArmorSettings Settings =>
            ModularPowerArmorMod.Settings ?? (ModularPowerArmorMod.Settings = new ModularPowerArmorSettings());

        public static List<ThingDef> AllModuleDefs => allModuleDefs;

        public static void CacheModuleDefs()
        {
            allModuleDefs = DefDatabase<ThingDef>.AllDefsListForReading
                .Where(def => def.GetCompProperties<CompProperties_ArmorModule>() != null)
                .ToList();
        }

        // ---- Quality ----

        /// <summary>1 at Normal quality, plus or minus the quality step for each tier above or below it.</summary>
        public static float QualityMultiplier(QualityCategory quality)
        {
            return Mathf.Max(0f, 1f + Settings.qualityStep * ((int)quality - (int)QualityCategory.Normal));
        }

        public static float QualityMultiplier(Thing module)
        {
            return QualityMultiplier(module.TryGetQuality(out QualityCategory quality) ? quality : QualityCategory.Normal);
        }

        /// <summary>Scales a factor's distance from 1: 1.15 at x1.3 becomes 1.195; 0.8 at x1.3 becomes 0.74.</summary>
        public static float ScaleFactor(float factor, float multiplier)
        {
            return Mathf.Max(0f, 1f + (factor - 1f) * multiplier);
        }

        /// <summary>
        /// Scales a drawback the other way round, so better quality lessens it: 0.8 at x1.3 becomes
        /// 0.846 and at x0.7 becomes 0.714.
        /// </summary>
        public static float ScalePenalty(float factor, float multiplier)
        {
            return Mathf.Max(0f, 1f + (factor - 1f) / Mathf.Max(multiplier, 0.1f));
        }

        public static bool HasQuality(ThingDef moduleDef)
        {
            return moduleDef != null && moduleDef.HasComp(typeof(CompQuality));
        }

        // ---- Module lookups ----

        public static CompProperties_ArmorModule PropsOf(Thing module)
        {
            return module?.def.GetCompProperties<CompProperties_ArmorModule>();
        }

        public static CompProperties_ArmorModule PropsOf(ThingDef moduleDef)
        {
            return moduleDef?.GetCompProperties<CompProperties_ArmorModule>();
        }

        public static float LoadCost(Thing module)
        {
            return module.def.GetStatValueAbstract(MPA_DefOf.MPA_ComputationalLoadCost);
        }

        public static float CapacityBonus(Thing module)
        {
            CompProperties_ArmorModule props = PropsOf(module);
            return props == null || props.computationalLoadBonus == 0f ? 0f : props.computationalLoadBonus * QualityMultiplier(module);
        }

        /// <summary>Computational load this module adds to every other modular piece worn with its host (second mind).</summary>
        public static float WornCapacityBonus(Thing module)
        {
            CompProperties_ArmorModule props = PropsOf(module);
            return props == null || props.wornComputationalLoadBonus == 0f ? 0f : props.wornComputationalLoadBonus * QualityMultiplier(module);
        }

        /// <summary>Load bonus <paramref name="armor"/> gets from modules in the other modular pieces its wearer has on.</summary>
        public static float WornCapacityBonusFor(CompModularArmor armor)
        {
            Pawn wearer = armor.Wearer;
            if (wearer == null)
            {
                return 0f;
            }
            float bonus = 0f;
            foreach (CompModularArmor other in WornModularArmor(wearer))
            {
                if (other == armor)
                {
                    continue;
                }
                List<Thing> modules = other.Modules;
                for (int i = 0; i < modules.Count; i++)
                {
                    bonus += WornCapacityBonus(modules[i]);
                }
            }
            return bonus;
        }

        public static bool IsSpent(Thing module)
        {
            return module.TryGetComp<CompArmorModule>()?.spent ?? false;
        }

        public static ArmorSlot DetectSlot(ThingDef apparelDef)
        {
            ApparelProperties apparel = apparelDef.apparel;
            if (apparel == null)
            {
                return ArmorSlot.Body;
            }
            bool coversTorso = apparel.bodyPartGroups != null && apparel.bodyPartGroups.Contains(BodyPartGroupDefOf.Torso);
            bool overhead = apparel.layers != null && apparel.layers.Contains(ApparelLayerDefOf.Overhead);
            return overhead && !coversTorso ? ArmorSlot.Helmet : ArmorSlot.Body;
        }

        // ---- Wearers ----

        public static IEnumerable<CompModularArmor> WornModularArmor(Pawn pawn)
        {
            List<Apparel> worn = pawn?.apparel?.WornApparel;
            if (worn == null)
            {
                yield break;
            }
            for (int i = 0; i < worn.Count; i++)
            {
                CompModularArmor comp = worn[i].GetComp<CompModularArmor>();
                if (comp != null)
                {
                    yield return comp;
                }
            }
        }

        public static CompModularArmor FirstWornModularArmor(Pawn pawn)
        {
            return WornModularArmor(pawn).FirstOrDefault();
        }

        public static int InstalledModuleCount(Pawn pawn)
        {
            int count = 0;
            foreach (CompModularArmor armor in WornModularArmor(pawn))
            {
                count += armor.Modules.Count;
            }
            return count;
        }

        public static bool HasWearerEffects(Pawn pawn)
        {
            foreach (CompModularArmor armor in WornModularArmor(pawn))
            {
                foreach (Thing module in armor.Modules)
                {
                    CompProperties_ArmorModule props = PropsOf(module);
                    if (props != null && props.HasWearerEffects && armor.IsModuleActive(module))
                    {
                        return true;
                    }
                }
            }
            return false;
        }

        /// <summary>The first active module on any piece the pawn wears whose properties match.</summary>
        public static Thing FirstActiveWornModule(Pawn pawn, System.Predicate<CompProperties_ArmorModule> match, out CompModularArmor host)
        {
            foreach (CompModularArmor armor in WornModularArmor(pawn))
            {
                List<Thing> modules = armor.Modules;
                for (int i = 0; i < modules.Count; i++)
                {
                    CompProperties_ArmorModule props = PropsOf(modules[i]);
                    if (props != null && match(props) && armor.IsModuleActive(modules[i]))
                    {
                        host = armor;
                        return modules[i];
                    }
                }
            }
            host = null;
            return null;
        }

        /// <summary>Fast lookup through the wearer hediff, for checks that run often (stats, rendering, combat).</summary>
        public static Hediff_ArmorModifications WearerHediff(Pawn pawn)
        {
            List<Hediff> hediffs = pawn?.health?.hediffSet?.hediffs;
            if (hediffs == null)
            {
                return null;
            }
            for (int i = 0; i < hediffs.Count; i++)
            {
                if (hediffs[i] is Hediff_ArmorModifications hediff)
                {
                    return hediff;
                }
            }
            return null;
        }

        public static bool SeesThroughObscurement(Pawn pawn)
        {
            return WearerHediff(pawn)?.SeesThroughObscurement ?? false;
        }

        public static bool PreventsStagger(Pawn pawn)
        {
            return WearerHediff(pawn)?.PreventsStagger ?? false;
        }

        /// <summary>
        /// Counts implanted and replaced parts for bionic synchronization. Parts that come out as an
        /// item below <paramref name="minTechLevel"/> (peg legs, simple prosthetics) don't count.
        /// </summary>
        public static int CountBionicImplants(Pawn pawn, TechLevel minTechLevel)
        {
            List<Hediff> hediffs = pawn?.health?.hediffSet?.hediffs;
            if (hediffs == null)
            {
                return 0;
            }
            int count = 0;
            for (int i = 0; i < hediffs.Count; i++)
            {
                HediffDef def = hediffs[i].def;
                if (!def.countsAsAddedPartOrImplant)
                {
                    continue;
                }
                ThingDef part = def.spawnThingOnRemoved;
                if (part != null && part.techLevel < minTechLevel)
                {
                    continue;
                }
                count++;
            }
            return count;
        }

        /// <summary>Changes whenever anything that feeds into the wearer hediff changes.</summary>
        public static int WornSignature(Pawn pawn)
        {
            int hash = Gen.HashCombineStruct(17, Settings.qualityStep);
            foreach (CompModularArmor armor in WornModularArmor(pawn))
            {
                hash = Gen.HashCombineInt(hash, armor.parent.thingIDNumber);
                hash = Gen.HashCombineStruct(hash, armor.IsOverloaded);
                foreach (Thing module in armor.Modules)
                {
                    hash = Gen.HashCombineInt(hash, module.thingIDNumber);
                    hash = Gen.HashCombineStruct(hash, IsSpent(module));
                }
            }
            hash = Gen.HashCombineInt(hash, CountBionicImplants(pawn, TechLevel.Undefined));
            hash = Gen.HashCombineInt(hash, CountBionicImplants(pawn, TechLevel.Spacer));
            return hash;
        }

        /// <summary>Call after modules change on armor the pawn is wearing, or after the pawn puts armor on or takes it off.</summary>
        public static void Notify_WornModulesChanged(Pawn pawn)
        {
            if (pawn?.health?.hediffSet == null)
            {
                return;
            }
            // Load bonuses cross between pieces (second mind), so every worn piece may have changed.
            foreach (CompModularArmor armor in WornModularArmor(pawn))
            {
                armor.ClearCaches();
            }
            Hediff_ArmorModifications hediff = pawn.health.hediffSet.GetFirstHediffOfDef(MPA_DefOf.MPA_ArmorModifications) as Hediff_ArmorModifications;
            bool wanted = HasWearerEffects(pawn);
            if (wanted && hediff == null)
            {
                pawn.health.AddHediff(MPA_DefOf.MPA_ArmorModifications);
            }
            else if (!wanted && hediff != null)
            {
                pawn.health.RemoveHediff(hediff);
            }
            else if (hediff != null)
            {
                hediff.SetDirty();
                pawn.health.Notify_HediffChanged(hediff);
            }
            RefreshGraphics(pawn);
        }

        public static void RefreshGraphics(Pawn pawn)
        {
            if (pawn.Spawned)
            {
                pawn.Drawer?.renderer?.SetAllGraphicsDirty();
            }
            if (pawn.IsColonist)
            {
                PortraitsCache.SetDirty(pawn);
            }
        }

        public static void Notify_SettingsChanged()
        {
            if (Current.ProgramState != ProgramState.Playing)
            {
                return;
            }
            foreach (Map map in Find.Maps)
            {
                foreach (Pawn pawn in map.mapPawns.AllPawnsSpawned.ToList())
                {
                    if (FirstWornModularArmor(pawn) != null)
                    {
                        Notify_WornModulesChanged(pawn);
                    }
                }
            }
        }

        /// <summary>Combines the wearer effects of every modification on every modular piece the pawn wears.</summary>
        public static HediffStage BuildWearerStage(Pawn pawn)
        {
            Dictionary<StatDef, float> statOffsets = new Dictionary<StatDef, float>();
            Dictionary<StatDef, float> statFactors = new Dictionary<StatDef, float>();
            Dictionary<PawnCapacityDef, float> capacityOffsets = new Dictionary<PawnCapacityDef, float>();
            Dictionary<PawnCapacityDef, float> capacityFactors = new Dictionary<PawnCapacityDef, float>();
            float painFactor = 1f;
            float bleedFactor = 1f;

            foreach (CompModularArmor armor in WornModularArmor(pawn))
            {
                foreach (Thing module in armor.Modules)
                {
                    CompProperties_ArmorModule props = PropsOf(module);
                    if (props == null || !props.HasWearerEffects || !armor.IsModuleActive(module))
                    {
                        continue;
                    }
                    float multiplier = armor.EffectMultiplier(module);
                    if (props.wearerStatOffsets != null)
                    {
                        foreach (StatModifier mod in props.wearerStatOffsets)
                        {
                            statOffsets.TryGetValue(mod.stat, out float current);
                            statOffsets[mod.stat] = current + mod.value * multiplier;
                        }
                    }
                    if (props.wearerStatFactors != null)
                    {
                        foreach (StatModifier mod in props.wearerStatFactors)
                        {
                            float current = statFactors.TryGetValue(mod.stat, out float existing) ? existing : 1f;
                            statFactors[mod.stat] = current * ScaleFactor(mod.value, multiplier);
                        }
                    }
                    if (props.wearerStatPenaltyFactors != null)
                    {
                        foreach (StatModifier mod in props.wearerStatPenaltyFactors)
                        {
                            float current = statFactors.TryGetValue(mod.stat, out float existing) ? existing : 1f;
                            statFactors[mod.stat] = current * ScalePenalty(mod.value, multiplier);
                        }
                    }
                    if (props.wearerCapacityModifiers != null)
                    {
                        foreach (PawnCapacityModifier capMod in props.wearerCapacityModifiers)
                        {
                            if (capMod.capacity == null)
                            {
                                continue;
                            }
                            if (capMod.offset != 0f)
                            {
                                capacityOffsets.TryGetValue(capMod.capacity, out float currentOffset);
                                capacityOffsets[capMod.capacity] = currentOffset + capMod.offset * multiplier;
                            }
                            if (capMod.postFactor != 1f)
                            {
                                float currentFactor = capacityFactors.TryGetValue(capMod.capacity, out float existing) ? existing : 1f;
                                capacityFactors[capMod.capacity] = currentFactor * ScaleFactor(capMod.postFactor, multiplier);
                            }
                        }
                    }
                    painFactor *= ScaleFactor(props.wearerPainFactor, multiplier);
                    bleedFactor *= ScaleFactor(props.wearerBleedFactor, multiplier);
                }
            }

            HediffStage stage = new HediffStage
            {
                becomeVisible = true,
                painFactor = painFactor,
                totalBleedFactor = bleedFactor
            };
            if (statOffsets.Count > 0)
            {
                stage.statOffsets = statOffsets.Select(kv => new StatModifier { stat = kv.Key, value = kv.Value }).ToList();
            }
            if (statFactors.Count > 0)
            {
                stage.statFactors = statFactors.Select(kv => new StatModifier { stat = kv.Key, value = kv.Value }).ToList();
            }
            IEnumerable<PawnCapacityDef> capacities = capacityOffsets.Keys.Union(capacityFactors.Keys);
            if (capacities.Any())
            {
                stage.capMods = capacities.Select(capacity => new PawnCapacityModifier
                {
                    capacity = capacity,
                    offset = capacityOffsets.TryGetValue(capacity, out float offset) ? offset : 0f,
                    postFactor = capacityFactors.TryGetValue(capacity, out float factor) ? factor : 1f
                }).ToList();
            }
            return stage;
        }

        public static string WornModulesDescription(Pawn pawn)
        {
            StringBuilder sb = new StringBuilder();
            foreach (CompModularArmor armor in WornModularArmor(pawn))
            {
                if (armor.Modules.Count == 0)
                {
                    continue;
                }
                if (sb.Length > 0)
                {
                    sb.AppendLine();
                }
                sb.Append(armor.parent.LabelCapNoCount).Append(": ");
                sb.Append(armor.Modules.Select(m => m.LabelNoCount).ToCommaList());
                if (armor.IsOverloaded)
                {
                    sb.Append(" (").Append("MPA_Overloaded".Translate()).Append(")");
                }
            }
            return sb.ToString();
        }

        /// <summary>One line per effect a stat can't show: senses, stagger, healing, the second heart, the longjump.</summary>
        public static List<string> SpecialEffectLines(Pawn pawn)
        {
            List<string> lines = new List<string>();
            if (DeathRefusalUtility.IsSustained(pawn))
            {
                lines.Add("MPA_Effect_Sustained".Translate(pawn.LabelShort, pawn.Named("PAWN")).Resolve());
            }
            foreach (CompModularArmor armor in WornModularArmor(pawn))
            {
                if (armor.IsOverloaded)
                {
                    lines.Add("MPA_Effect_Overloaded".Translate(armor.parent.LabelShort).Resolve());
                }
                foreach (Thing module in armor.Modules)
                {
                    CompProperties_ArmorModule props = PropsOf(module);
                    if (props == null)
                    {
                        continue;
                    }
                    string name = module.LabelCapNoCount;
                    if (props.refuseDeath)
                    {
                        lines.Add((IsSpent(module) ? "MPA_Effect_HeartSpent" : "MPA_Effect_HeartReady").Translate(name).Resolve());
                    }
                    if (!armor.IsModuleActive(module))
                    {
                        continue;
                    }
                    float multiplier = armor.EffectMultiplier(module);
                    if (props.seeThroughObscurement)
                    {
                        lines.Add("MPA_Effect_SeeThrough".Translate(name).Resolve());
                    }
                    if (props.preventStagger)
                    {
                        lines.Add("MPA_Effect_NoStagger".Translate(name).Resolve());
                    }
                    if (props.HasCoveredPartEffects)
                    {
                        lines.Add("MPA_Effect_Regenerators".Translate(
                            name,
                            armor.parent.LabelShort,
                            ScaleFactor(props.coveredPainFactor, multiplier).ToStringPercent(),
                            (props.coveredHealPerDay * multiplier).ToString("0.#"),
                            props.coveredTendIntervalTicks.ToStringTicksToPeriod(),
                            Mathf.Clamp01(props.coveredTendQuality * multiplier).ToStringPercent()).Resolve());
                    }
                    if (props.wornComputationalLoadBonus > 0f)
                    {
                        lines.Add("MPA_Effect_WornLoad".Translate(name, WornCapacityBonus(module).ToString("0.#")).Resolve());
                    }
                    if (props.longjump != null)
                    {
                        int left = module.TryGetComp<CompArmorModule>()?.LongjumpTicksLeft ?? 0;
                        lines.Add("MPA_Effect_Longjump".Translate(
                            name,
                            LongjumpUtility.Range(armor, module).ToString("0.#"),
                            LongjumpUtility.CooldownTicks(armor, module).ToStringTicksToPeriod(),
                            left > 0 ? "MPA_Effect_LongjumpLeft".Translate(left.ToStringTicksToPeriod()) : "MPA_Effect_LongjumpReady".Translate()).Resolve());
                    }
                }
            }
            return lines;
        }

        // ---- Generated pawns ----

        /// <summary>Gives armor worn by a freshly generated non-player pawn a chance to come with modifications.</summary>
        public static void TryGiveNpcModules(CompModularArmor armor, Pawn pawn)
        {
            if (pawn == null || pawn.Spawned || pawn.Faction == null || pawn.Faction.IsPlayer)
            {
                return;
            }
            if (armor.Modules.Count > 0 || !Rand.Chance(Settings.npcModuleChance))
            {
                return;
            }
            int wanted = Rand.RangeInclusive(1, 3);
            foreach (ThingDef def in allModuleDefs.InRandomOrder())
            {
                if (wanted <= 0)
                {
                    break;
                }
                CompProperties_ArmorModule props = PropsOf(def);
                if (!props.generateOnNpcs || !props.FitsSlot(armor.Slot) || armor.HasModuleOfDef(def))
                {
                    continue;
                }
                Thing module = ThingMaker.MakeThing(def);
                module.TryGetComp<CompQuality>()?.SetQuality(
                    QualityUtility.GenerateQualityGeneratingPawn(pawn.kindDef, def),
                    ArtGenerationContext.Outsider);
                if (armor.TryInstall(module, null))
                {
                    wanted--;
                }
            }
        }

        // ---- Work ----

        public static AcceptanceReport CanWorkOnArmor(Pawn pawn)
        {
            if (pawn.Downed)
            {
                return "MPA_Reason_Downed".Translate(pawn.LabelShort, pawn).Resolve();
            }
            if (!pawn.health.capacities.CapableOf(PawnCapacityDefOf.Manipulation))
            {
                return "MPA_Reason_NoManipulation".Translate(pawn.LabelShort, pawn).Resolve();
            }
            return true;
        }

        public static int WorkTicks(Pawn pawn, Thing module)
        {
            CompProperties_ArmorModule props = PropsOf(module);
            float baseTicks = props?.installTicks ?? 600;
            float speed = Mathf.Max(0.2f, pawn.GetStatValue(StatDefOf.GeneralLaborSpeed));
            return Mathf.Max(60, Mathf.RoundToInt(baseTicks / speed));
        }

        /// <summary>Closest reachable module of each type and quality on the pawn's map.</summary>
        public static List<Thing> AvailableModulesFor(Pawn pawn)
        {
            List<Thing> result = new List<Thing>();
            Map map = pawn.MapHeld;
            if (map == null)
            {
                return result;
            }
            IntVec3 origin = pawn.PositionHeld;
            Dictionary<QualityCategory, Thing> closest = new Dictionary<QualityCategory, Thing>();
            foreach (ThingDef def in allModuleDefs)
            {
                closest.Clear();
                foreach (Thing thing in map.listerThings.ThingsOfDef(def))
                {
                    if (!thing.Spawned || thing.IsForbidden(pawn) || !pawn.CanReserveAndReach(thing, PathEndMode.ClosestTouch, Danger.Deadly))
                    {
                        continue;
                    }
                    QualityCategory quality = thing.TryGetQuality(out QualityCategory q) ? q : QualityCategory.Normal;
                    if (!closest.TryGetValue(quality, out Thing current)
                        || origin.DistanceToSquared(thing.Position) < origin.DistanceToSquared(current.Position))
                    {
                        closest[quality] = thing;
                    }
                }
                result.AddRange(closest.OrderByDescending(kv => kv.Key).Select(kv => kv.Value));
            }
            return result;
        }
    }
}
