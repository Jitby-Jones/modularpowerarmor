using System.Collections.Generic;
using RimWorld;
using Verse;

namespace ModularPowerArmor
{
    /// <summary>
    /// Defines an armor modification. Every value here is the Normal-quality baseline; quality
    /// scales each effect by <see cref="ModularPowerArmorSettings.qualityStep"/> per tier.
    /// Offsets are multiplied by the quality multiplier, and factors have their distance from
    /// 1 multiplied (so a 1.15x bonus becomes 1.1725x at Good quality).
    /// </summary>
    public class CompProperties_ArmorModule : CompProperties
    {
        /// <summary>Armor pieces this modification can be installed in.</summary>
        public List<ArmorSlot> slots = new List<ArmorSlot>();

        // Effects on whoever wears the modified armor. Applied through a hediff, so they show up
        // in the health tab and in every stat breakdown.
        public List<StatModifier> wearerStatOffsets;
        public List<StatModifier> wearerStatFactors;
        public List<PawnCapacityModifier> wearerCapacityModifiers;
        public float wearerPainFactor = 1f;
        public float wearerBleedFactor = 1f;

        // Effects on the armor piece itself (armor ratings, flammability, ...).
        public List<StatModifier> armorStatOffsets;
        public List<StatModifier> armorStatFactors;

        /// <summary>Extra computational load the host piece can support. Not affected by bionic synchronization.</summary>
        public float computationalLoadBonus;

        /// <summary>Boost to every other modification on the same piece, per qualifying implant in the wearer.</summary>
        public float bionicSyncPerImplant;

        /// <summary>Implants with a removable part below this tech level don't count for bionic synchronization.</summary>
        public TechLevel bionicSyncMinTechLevel = TechLevel.Spacer;

        /// <summary>Base installation or removal time, before the worker's general labor speed.</summary>
        public int installTicks = 600;

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

        public bool HasWearerEffects =>
            !wearerStatOffsets.NullOrEmpty()
            || !wearerStatFactors.NullOrEmpty()
            || !wearerCapacityModifiers.NullOrEmpty()
            || wearerPainFactor != 1f
            || wearerBleedFactor != 1f;

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
            if (!parentDef.HasComp(typeof(CompQuality)))
            {
                yield return "armor module has no CompQuality; it will always count as Normal quality";
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
            foreach (StatDrawEntry entry in ArmorModuleStatDisplay.EntriesFor(this, quality))
            {
                yield return entry;
            }
        }
    }
}
