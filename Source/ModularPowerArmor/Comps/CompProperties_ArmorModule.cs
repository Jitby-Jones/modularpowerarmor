using System.Collections.Generic;
using RimWorld;
using Verse;

namespace ModularPowerArmor
{
    /// <summary>
    /// Defines an armor modification. Every value here is the Normal-quality baseline; quality
    /// scales each effect by <see cref="ModularPowerArmorSettings.qualityStep"/> per tier.
    /// Offsets are multiplied by the quality multiplier, and factors have their distance from
    /// 1 multiplied (so a 1.15x bonus becomes 1.1725x at Good quality). Drawbacks
    /// (<see cref="wearerStatPenaltyFactors"/>) work the other way: better quality lessens them.
    /// </summary>
    public class CompProperties_ArmorModule : CompProperties
    {
        /// <summary>Armor pieces this modification can be installed in.</summary>
        public List<ArmorSlot> slots = new List<ArmorSlot>();

        /// <summary>Modifications that share a tag can't be installed in the same piece (both kinds of plating, say).</summary>
        public List<string> exclusionTags;

        // Effects on whoever wears the modified armor. Applied through a hediff, so they show up
        // in the health tab and in every stat breakdown.
        public List<StatModifier> wearerStatOffsets;
        public List<StatModifier> wearerStatFactors;

        /// <summary>Stat factors that are a drawback of the modification; higher quality lessens them.</summary>
        public List<StatModifier> wearerStatPenaltyFactors;

        public List<PawnCapacityModifier> wearerCapacityModifiers;
        public float wearerPainFactor = 1f;
        public float wearerBleedFactor = 1f;

        // Effects on the body parts the host armor piece covers (neuromemetic regenerators).

        /// <summary>Multiplies the pain from injuries and conditions on covered body parts.</summary>
        public float coveredPainFactor = 1f;

        /// <summary>Injury severity healed per day on covered body parts and the organs inside them, scars included.</summary>
        public float coveredHealPerDay;

        /// <summary>Ticks between tending a random bleeding wound on a covered body part. 0 to never tend.</summary>
        public int coveredTendIntervalTicks;

        /// <summary>Quality of those tends, before the modification's own quality.</summary>
        public float coveredTendQuality = 0.8f;

        /// <summary>The wearer sees through blindness, darkness, fog and smoke (multispectral sensor array).</summary>
        public bool seeThroughObscurement;

        /// <summary>The wearer can't be staggered by hits (rigidity matrix).</summary>
        public bool preventStagger;

        /// <summary>Keeps the wearer alive once when their head is destroyed (second heart). Used up afterwards.</summary>
        public bool refuseDeath;

        /// <summary>Gives the wearer a leap ability (longjump hydraulics).</summary>
        public LongjumpProperties longjump;

        // Effects on the armor piece itself (armor ratings, flammability, ...).
        public List<StatModifier> armorStatOffsets;
        public List<StatModifier> armorStatFactors;

        /// <summary>Extra computational load the host piece can support. Not affected by bionic synchronization.</summary>
        public float computationalLoadBonus;

        /// <summary>Extra computational load for every other modular piece worn together with the host piece.</summary>
        public float wornComputationalLoadBonus;

        /// <summary>Boost to every other modification on the same piece, per qualifying implant in the wearer.</summary>
        public float bionicSyncPerImplant;

        /// <summary>Implants with a removable part below this tech level don't count for bionic synchronization.</summary>
        public TechLevel bionicSyncMinTechLevel = TechLevel.Spacer;

        /// <summary>Base installation or removal time, before the worker's general labor speed.</summary>
        public int installTicks = 600;

        /// <summary>Whether armor worn by generated non-player pawns can come with this modification.</summary>
        public bool generateOnNpcs = true;

        // Visuals drawn on the wearer while the modification is installed, per armor slot.
        public List<PawnRenderNodeProperties> bodyRenderNodes;
        public List<PawnRenderNodeProperties> helmetRenderNodes;

        public CompProperties_ArmorModule()
        {
            compClass = typeof(CompArmorModule);
        }

        public bool FitsSlot(ArmorSlot slot)
        {
            return slots.Contains(slot);
        }

        public bool ExcludedBy(CompProperties_ArmorModule other)
        {
            if (exclusionTags.NullOrEmpty() || other?.exclusionTags == null)
            {
                return false;
            }
            for (int i = 0; i < exclusionTags.Count; i++)
            {
                if (other.exclusionTags.Contains(exclusionTags[i]))
                {
                    return true;
                }
            }
            return false;
        }

        /// <summary>Effects that need the wearer hediff (stat and capacity changes, pain, healing, senses, ...).</summary>
        public bool HasWearerEffects =>
            !wearerStatOffsets.NullOrEmpty()
            || !wearerStatFactors.NullOrEmpty()
            || !wearerStatPenaltyFactors.NullOrEmpty()
            || !wearerCapacityModifiers.NullOrEmpty()
            || wearerPainFactor != 1f
            || wearerBleedFactor != 1f
            || HasCoveredPartEffects
            || seeThroughObscurement
            || preventStagger;

        public bool HasCoveredPartEffects => coveredPainFactor != 1f || coveredHealPerDay > 0f || coveredTendIntervalTicks > 0;

        public List<PawnRenderNodeProperties> RenderNodesFor(ArmorSlot slot)
        {
            return slot == ArmorSlot.Helmet ? helmetRenderNodes : bodyRenderNodes;
        }

        public override void ResolveReferences(ThingDef parentDef)
        {
            base.ResolveReferences(parentDef);
            ResolveRenderNodes(bodyRenderNodes, "ApparelBody");
            ResolveRenderNodes(helmetRenderNodes, "ApparelHead");
        }

        private static void ResolveRenderNodes(List<PawnRenderNodeProperties> nodes, string defaultParentTag)
        {
            if (nodes == null)
            {
                return;
            }
            foreach (PawnRenderNodeProperties node in nodes)
            {
                if (node.parentTagDef == null)
                {
                    node.parentTagDef = DefDatabase<PawnRenderNodeTagDef>.GetNamedSilentFail(defaultParentTag);
                }
                if (node.nodeClass == null || !typeof(PawnRenderNode_ArmorModule).IsAssignableFrom(node.nodeClass))
                {
                    node.nodeClass = typeof(PawnRenderNode_ArmorModule);
                }
                if (node.workerClass == null || !typeof(PawnRenderNodeWorker_ArmorModule).IsAssignableFrom(node.workerClass))
                {
                    node.workerClass = typeof(PawnRenderNodeWorker_ArmorModule);
                }
                node.ResolveReferencesRecursive();
            }
        }

        public override IEnumerable<string> ConfigErrors(ThingDef parentDef)
        {
            foreach (string error in base.ConfigErrors(parentDef))
            {
                yield return error;
            }
            if (slots.NullOrEmpty())
            {
                yield return "armor module has no slots";
            }
            if (slots.Contains(ArmorSlot.Auto))
            {
                yield return "armor module slots must be Body or Helmet, not Auto";
            }
            if (!wearerCapacityModifiers.NullOrEmpty())
            {
                foreach (PawnCapacityModifier capMod in wearerCapacityModifiers)
                {
                    if (capMod.capacity == null)
                    {
                        yield return "wearerCapacityModifiers entry with no capacity";
                    }
                }
            }
            if (longjump != null && longjump.range <= 0f)
            {
                yield return "longjump range must be above 0";
            }
            if (refuseDeath && !FitsSlot(ArmorSlot.Body))
            {
                yield return "refuseDeath only works on body armor, which stays on when the head is lost";
            }
        }

        public override IEnumerable<StatDrawEntry> SpecialDisplayStats(StatRequest req)
        {
            foreach (StatDrawEntry entry in base.SpecialDisplayStats(req))
            {
                yield return entry;
            }
            QualityCategory quality = QualityCategory.Normal;
            if (req.HasThing && req.Thing.TryGetQuality(out QualityCategory thingQuality))
            {
                quality = thingQuality;
            }
            ThingDef def = req.Def as ThingDef ?? req.Thing?.def;
            foreach (StatDrawEntry entry in ArmorModuleStatDisplay.EntriesFor(this, def, quality, req.Thing))
            {
                yield return entry;
            }
        }
    }

    public class LongjumpProperties
    {
        /// <summary>Leap range in cells at Normal quality.</summary>
        public float range = 20f;

        /// <summary>Recharge time at Normal quality.</summary>
        public int cooldownTicks = 7500;
    }
}
