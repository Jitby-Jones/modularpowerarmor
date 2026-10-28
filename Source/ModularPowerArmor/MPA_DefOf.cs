using RimWorld;
using Verse;

namespace ModularPowerArmor
{
    [DefOf]
    public static class MPA_DefOf
    {
        public static StatDef MPA_ComputationalLoad;
        public static StatDef MPA_ComputationalLoadCost;

        public static StatCategoryDef MPA_ArmorModification;

        public static HediffDef MPA_ArmorModifications;

        public static JobDef MPA_InstallArmorModule;
        public static JobDef MPA_RemoveArmorModule;

        static MPA_DefOf()
        {
            DefOfHelper.EnsureInitializedInCtor(typeof(MPA_DefOf));
        }
    }
}
