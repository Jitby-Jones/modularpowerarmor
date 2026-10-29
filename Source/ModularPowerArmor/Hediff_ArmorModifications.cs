using System.Collections.Generic;
using RimWorld;
using UnityEngine;
using Verse;

namespace ModularPowerArmor
{
    /// <summary>
    /// Applies the combined wearer effects of every modification on the armor a pawn is wearing.
    /// The stage is rebuilt from the worn armor whenever modules, quality or implants change, so
    /// effects show up in the health tab and in stat breakdowns like any other hediff.
    /// Also runs the effects that need ticking or body-part checks: neuromemetic regenerators heal,
    /// tend and numb the parts their armor piece covers.
    /// </summary>
    public class Hediff_ArmorModifications : Hediff
    {
        // Apparel removal isn't reliably reported to apparel comps, so check the worn armor regularly.
        private const int ValidateInterval = 120;
        private const int HealInterval = 600;

        [Unsaved] private HediffStage stage;
        [Unsaved] private bool dirty = true;
        [Unsaved] private int lastSignature;
        [Unsaved] private bool pendingRemoval;
        [Unsaved] private bool seesThroughObscurement;
        [Unsaved] private float sightFloor;
        [Unsaved] private bool preventsStagger;
        [Unsaved] private List<CoveredEffect> covered = new List<CoveredEffect>();

        private static readonly List<Hediff> tmpHediffs = new List<Hediff>();

        /// <summary>What one regenerator does for the body parts its armor piece covers.</summary>
        private struct CoveredEffect
        {
            public ApparelProperties coverage;
            public float painFactor;
            public float healPerDay;
            public int tendInterval;
            public float tendQuality;
        }

        public override HediffStage CurStage
        {
            get
            {
                EnsureCalculated();
                return stage;
            }
        }

        public override bool ShouldRemove => pendingRemoval || base.ShouldRemove;

        /// <summary>A multispectral sensor array is working: blindness, darkness, fog and smoke don't hinder the wearer.</summary>
        public bool SeesThroughObscurement
        {
            get
            {
                EnsureCalculated();
                return seesThroughObscurement;
            }
        }

        /// <summary>The wearer's sight never drops below this while <see cref="SeesThroughObscurement"/>.</summary>
        public float SightFloor
        {
            get
            {
                EnsureCalculated();
                return sightFloor;
            }
        }

        public bool PreventsStagger
        {
            get
            {
                EnsureCalculated();
                return preventsStagger;
            }
        }

        public override string LabelInBrackets
        {
            get
            {
                int count = ArmorModuleUtility.InstalledModuleCount(pawn);
                return count > 0 ? "MPA_HediffModuleCount".Translate(count).Resolve() : base.LabelInBrackets;
            }
        }

        public override string TipStringExtra
        {
            get
            {
                string modules = ArmorModuleUtility.WornModulesDescription(pawn);
                List<string> effects = ArmorModuleUtility.SpecialEffectLines(pawn);
                if (effects.Count > 0)
                {
                    modules += "\n\n" + effects.ToLineList("  - ");
                }
                string baseTip = base.TipStringExtra;
                return baseTip.NullOrEmpty() ? modules : baseTip + "\n" + modules;
            }
        }

        /// <summary>Takes the regenerators' share off the pain of injuries on the body parts they cover.</summary>
        public override float PainOffset
        {
            get
            {
                float offset = base.PainOffset;
                EnsureCalculated();
                if (covered.Count == 0 || pawn.Dead)
                {
                    return offset;
                }
                List<Hediff> hediffs = pawn.health.hediffSet.hediffs;
                for (int i = 0; i < hediffs.Count; i++)
                {
                    Hediff hediff = hediffs[i];
                    if (hediff == this || hediff.Part == null)
                    {
                        continue;
                    }
                    float factor = CoveredPainFactor(hediff.Part);
                    if (factor < 1f)
                    {
                        float pain = hediff.PainOffset;
                        if (pain > 0f)
                        {
                            offset -= pain * (1f - factor);
                        }
                    }
                }
                return offset;
            }
        }

        public void SetDirty()
        {
            dirty = true;
            pendingRemoval = false;
        }

        private void EnsureCalculated()
        {
            if (dirty || stage == null)
            {
                Recalculate();
            }
        }

        private void Recalculate()
        {
            dirty = false;
            stage = ArmorModuleUtility.BuildWearerStage(pawn);
            lastSignature = ArmorModuleUtility.WornSignature(pawn);
            seesThroughObscurement = false;
            sightFloor = 0f;
            preventsStagger = false;
            covered.Clear();
            foreach (CompModularArmor armor in ArmorModuleUtility.WornModularArmor(pawn))
            {
                foreach (Thing module in armor.Modules)
                {
                    CompProperties_ArmorModule props = ArmorModuleUtility.PropsOf(module);
                    if (props == null || !armor.IsModuleActive(module))
                    {
                        continue;
                    }
                    float multiplier = armor.EffectMultiplier(module);
                    if (props.seeThroughObscurement)
                    {
                        seesThroughObscurement = true;
                        sightFloor = Mathf.Max(sightFloor, SightFactor(props, multiplier));
                    }
                    preventsStagger |= props.preventStagger;
                    if (props.HasCoveredPartEffects && armor.Apparel?.def.apparel != null)
                    {
                        covered.Add(new CoveredEffect
                        {
                            coverage = armor.Apparel.def.apparel,
                            painFactor = ArmorModuleUtility.ScaleFactor(props.coveredPainFactor, multiplier),
                            healPerDay = props.coveredHealPerDay * multiplier,
                            tendInterval = props.coveredTendIntervalTicks,
                            tendQuality = Mathf.Clamp01(props.coveredTendQuality * multiplier)
                        });
                    }
                }
            }
        }

        /// <summary>The sensor's own sight bonus, so a blind wearer sees as well as a sighted one with the sensor.</summary>
        private static float SightFactor(CompProperties_ArmorModule props, float multiplier)
        {
            float factor = 1f;
            if (props.wearerCapacityModifiers != null)
            {
                foreach (PawnCapacityModifier capMod in props.wearerCapacityModifiers)
                {
                    if (capMod.capacity == PawnCapacityDefOf.Sight && capMod.postFactor != 1f)
                    {
                        factor *= ArmorModuleUtility.ScaleFactor(capMod.postFactor, multiplier);
                    }
                }
            }
            return factor;
        }

        private float CoveredPainFactor(BodyPartRecord part)
        {
            float factor = 1f;
            for (int i = 0; i < covered.Count; i++)
            {
                if (covered[i].painFactor < factor && Covers(covered[i].coverage, part))
                {
                    factor = covered[i].painFactor;
                }
            }
            return factor;
        }

        /// <summary>Whether the armor covers a part, counting organs inside a covered part.</summary>
        private static bool Covers(ApparelProperties coverage, BodyPartRecord part)
        {
            for (BodyPartRecord current = part; current != null; current = current.parent)
            {
                if (coverage.CoversBodyPart(current))
                {
                    return true;
                }
                if (current.depth != BodyPartDepth.Inside)
                {
                    return false;
                }
            }
            return false;
        }

#if RW_1_5
        public override void Tick()
        {
            base.Tick();
            DoInterval(1);
        }
#else
        public override void TickInterval(int delta)
        {
            base.TickInterval(delta);
            DoInterval(delta);
        }
#endif

        private void DoInterval(int delta)
        {
            if (IsHashIntervalTick(ValidateInterval, delta))
            {
                Validate();
            }
            if (pendingRemoval || pawn.Dead)
            {
                return;
            }
            EnsureCalculated();
            if (covered.Count == 0)
            {
                return;
            }
            bool heal = IsHashIntervalTick(HealInterval, delta);
            for (int i = 0; i < covered.Count; i++)
            {
                CoveredEffect effect = covered[i];
                if (effect.tendInterval > 0 && IsHashIntervalTick(effect.tendInterval, delta))
                {
                    TendRandomBleedingWound(effect);
                }
                if (heal && effect.healPerDay > 0f)
                {
                    HealRandomInjury(effect, effect.healPerDay * HealInterval / GenDate.TicksPerDay);
                }
            }
        }

        private bool IsHashIntervalTick(int interval, int delta)
        {
#if RW_1_5
            return pawn.IsHashIntervalTick(interval);
#else
            return pawn.IsHashIntervalTick(interval, delta);
#endif
        }

        private void TendRandomBleedingWound(CoveredEffect effect)
        {
            tmpHediffs.Clear();
            List<Hediff> hediffs = pawn.health.hediffSet.hediffs;
            for (int i = 0; i < hediffs.Count; i++)
            {
                Hediff hediff = hediffs[i];
                if (hediff.Part != null && hediff.Bleeding && hediff.TendableNow() && Covers(effect.coverage, hediff.Part))
                {
                    tmpHediffs.Add(hediff);
                }
            }
            if (tmpHediffs.TryRandomElement(out Hediff wound))
            {
                wound.Tended(effect.tendQuality, 1f);
                if (pawn.Spawned)
                {
                    FleckMaker.ThrowMetaIcon(pawn.Position, pawn.Map, FleckDefOf.HealingCross);
                }
            }
            tmpHediffs.Clear();
        }

        private void HealRandomInjury(CoveredEffect effect, float amount)
        {
            tmpHediffs.Clear();
            List<Hediff> hediffs = pawn.health.hediffSet.hediffs;
            for (int i = 0; i < hediffs.Count; i++)
            {
                if (hediffs[i] is Hediff_Injury injury && injury.Part != null && Covers(effect.coverage, injury.Part))
                {
                    tmpHediffs.Add(injury);
                }
            }
            if (tmpHediffs.TryRandomElement(out Hediff chosen))
            {
                chosen.Heal(amount);
            }
            tmpHediffs.Clear();
        }

        /// <summary>
        /// Catches changes this hediff isn't told about directly, such as an implant being installed
        /// (bionic synchronization) or the armor being taken off by something that skips the usual notifications.
        /// </summary>
        private void Validate()
        {
            pendingRemoval = !ArmorModuleUtility.HasWearerEffects(pawn);
            if (pendingRemoval)
            {
                return;
            }
            if (ArmorModuleUtility.WornSignature(pawn) != lastSignature)
            {
                dirty = true;
                pawn.health.Notify_HediffChanged(this);
            }
        }

        public override void PostRemoved()
        {
            base.PostRemoved();
            covered.Clear();
        }
    }
}
