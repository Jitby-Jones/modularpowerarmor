using Verse;

namespace ModularPowerArmor
{
    /// <summary>
    /// Makes an apparel def accept modifications. Usually added at startup from a
    /// <see cref="ModularArmorTargetDef"/>, but it can also be put on a def directly in XML.
    /// </summary>
    public class CompProperties_ModularArmor : CompProperties
    {
        public ArmorSlot slot = ArmorSlot.Auto;

        /// <summary>Used only when the def has no MPA_ComputationalLoad stat base of its own.</summary>
        public float defaultComputationalLoad = 8f;

        /// <summary>Which armor's module art to use; see <see cref="ModularArmorTarget.fit"/>.</summary>
        public string fit;

        public CompProperties_ModularArmor()
        {
            compClass = typeof(CompModularArmor);
        }

        public override void ResolveReferences(ThingDef parentDef)
        {
            base.ResolveReferences(parentDef);
            if (slot == ArmorSlot.Auto)
            {
                slot = ArmorModuleUtility.DetectSlot(parentDef);
            }
        }
    }
}
