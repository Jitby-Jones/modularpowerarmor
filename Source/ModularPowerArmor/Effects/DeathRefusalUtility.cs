using System.Collections.Generic;
using RimWorld;
using Verse;

namespace ModularPowerArmor
{
    /// <summary>The second heart: refuses the wearer's death once, when their head is destroyed.</summary>
    public static class DeathRefusalUtility
    {
        /// <summary>
        /// Called as the pawn is about to die. Refuses the death when the head is gone, a working second
        /// heart is installed, and losing the head is the only thing killing them: bleeding out, a
        /// destroyed heart or torso, or any other fatal wound still kills.
        /// </summary>
        public static bool TryRefuseDeath(Pawn pawn, DamageInfo? dinfo, Hediff exactCulprit)
        {
            if (pawn == null || pawn.Dead || pawn.health?.hediffSet == null || pawn.apparel == null)
            {
                return false;
            }
            HediffSet hediffSet = pawn.health.hediffSet;
            if (!HeadDestroyed(pawn) || hediffSet.HasHediff(MPA_DefOf.MPA_DeathRefused))
            {
                return false;
            }
            Thing heart = ArmorModuleUtility.FirstActiveWornModule(pawn, props => props.refuseDeath, out CompModularArmor armor);
            if (heart == null || !WouldSurviveWithoutHead(pawn))
            {
                return false;
            }

            // Used up before anything else happens, so nothing below can trigger a second refusal.
            CompArmorModule heartComp = heart.TryGetComp<CompArmorModule>();
            heartComp.spent = true;

            Hediff_DeathRefused hediff = (Hediff_DeathRefused)HediffMaker.MakeHediff(MPA_DefOf.MPA_DeathRefused, pawn);
            hediff.killingBlow = DescribeKillingBlow(dinfo, exactCulprit);
            pawn.health.AddHediff(hediff);
            armor.Notify_ModulesChanged();
            TendAllWounds(pawn);

            if (pawn.Spawned)
            {
                FleckMaker.ThrowMetaIcon(pawn.Position, pawn.Map, FleckDefOf.HealingCross);
            }
            // The colony's own pawns get the critical alert (Alert_DeathRefused); prisoners and guests a message.
            if (pawn.Faction != Faction.OfPlayer && pawn.HostFaction == Faction.OfPlayer)
            {
                Messages.Message("MPA_DeathRefusedMessage".Translate(pawn.LabelShort, pawn.Named("PAWN")), pawn, MessageTypeDefOf.NegativeHealthEvent);
            }
            return true;
        }

        /// <summary>
        /// Mirrors Pawn_HealthTracker.ShouldBeDead with the head's capacities taken over by the
        /// second heart: consciousness, and breathing when only the neck's airway is gone.
        /// </summary>
        private static bool WouldSurviveWithoutHead(Pawn pawn)
        {
            Pawn_HealthTracker health = pawn.health;
            List<Hediff> hediffs = health.hediffSet.hediffs;
            for (int i = 0; i < hediffs.Count; i++)
            {
                if (hediffs[i].CauseDeathNow())
                {
                    return false;
                }
            }
            bool flesh = pawn.RaceProps.IsFlesh;
            List<PawnCapacityDef> capacities = DefDatabase<PawnCapacityDef>.AllDefsListForReading;
            for (int i = 0; i < capacities.Count; i++)
            {
                PawnCapacityDef capacity = capacities[i];
                if (!(flesh ? capacity.lethalFlesh : capacity.lethalMechanoids) || capacity == PawnCapacityDefOf.Consciousness)
                {
                    continue;
                }
                if (capacity == PawnCapacityDefOf.Breathing && SustainedBreathing(health.hediffSet) > 0f)
                {
                    continue;
                }
                if (!health.capacities.CapableOf(capacity))
                {
                    return false;
                }
            }
            if (PawnCapacityUtility.CalculatePartEfficiency(health.hediffSet, pawn.RaceProps.body.corePart) <= 0.0001f)
            {
                return false;
            }
            return !health.ShouldBeDeadFromLethalDamageThreshold();
        }

        /// <summary>
        /// Breathing for a sustained pawn whose airway went with the head (a destroyed neck): the
        /// lungs still work, so the second heart keeps them going at half strength.
        /// </summary>
        public static float SustainedBreathing(HediffSet hediffSet)
        {
            if (PawnCapacityUtility.CalculateTagEfficiency(hediffSet, BodyPartTagDefOf.BreathingPathway, 1f) > 0f)
            {
                return 0f; // the airway is intact; vanilla breathing applies
            }
            return Hediff_DeathRefused.SustainedConsciousness * PawnCapacityUtility.CalculateTagEfficiency(hediffSet, BodyPartTagDefOf.BreathingSource);
        }

        /// <summary>The body has a head, and it is gone.</summary>
        private static bool HeadDestroyed(Pawn pawn)
        {
            HediffSet hediffSet = pawn.health.hediffSet;
            if (hediffSet.HasHead)
            {
                return false;
            }
            List<BodyPartRecord> parts = pawn.RaceProps.body.AllParts;
            for (int i = 0; i < parts.Count; i++)
            {
                if (parts[i].def == BodyPartDefOf.Head)
                {
                    return true;
                }
            }
            return false;
        }

        /// <summary>The head (or what it held) is back: regrown, regenerated or replaced.</summary>
        public static bool HeadRestored(Pawn pawn)
        {
            HediffSet hediffSet = pawn.health.hediffSet;
            return hediffSet.HasHead
                && PawnCapacityUtility.CalculateTagEfficiency(hediffSet, BodyPartTagDefOf.ConsciousnessSource) > 0f;
        }

        public static bool IsSustained(Pawn pawn)
        {
            return pawn?.health?.hediffSet != null && pawn.health.hediffSet.HasHediff(MPA_DefOf.MPA_DeathRefused);
        }

        private static void TendAllWounds(Pawn pawn)
        {
            List<Hediff> tendable = new List<Hediff>();
            List<Hediff> hediffs = pawn.health.hediffSet.hediffs;
            for (int i = 0; i < hediffs.Count; i++)
            {
                if (hediffs[i].TendableNow())
                {
                    tendable.Add(hediffs[i]);
                }
            }
            for (int i = 0; i < tendable.Count; i++)
            {
                tendable[i].Tended(TendQuality, 1f, i);
            }
        }

        public const float TendQuality = 0.8f;

        private static string DescribeKillingBlow(DamageInfo? dinfo, Hediff exactCulprit)
        {
            if (dinfo.HasValue && dinfo.Value.Def != null)
            {
                DamageInfo info = dinfo.Value;
                string part = info.HitPart?.Label ?? exactCulprit?.Part?.Label ?? "MPA_KillingBlowHead".Translate().Resolve();
                TaggedString text = "MPA_KillingBlow".Translate(info.Amount.ToString("0.#"), info.Def.label, part);
                if (info.Instigator != null)
                {
                    text += " " + "MPA_KillingBlowBy".Translate(info.Instigator.LabelShort);
                }
                if (info.Weapon != null && info.Weapon != info.Instigator?.def)
                {
                    text += " " + "MPA_KillingBlowWith".Translate(info.Weapon.label);
                }
                return text.Resolve().CapitalizeFirst() + ".";
            }
            if (exactCulprit != null)
            {
                return exactCulprit.LabelCap;
            }
            return "MPA_KillingBlowUnknown".Translate().Resolve();
        }
    }
}
