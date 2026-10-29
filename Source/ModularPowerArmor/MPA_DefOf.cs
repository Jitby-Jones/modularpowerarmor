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
        public static HediffDef MPA_DeathRefused;

        public static ResearchProjectDef MPA_Research_ArmorModification;
        public static ResearchProjectDef MPA_Research_AdvancedModules;

        public static JobDef MPA_InstallArmorModule;
        public static JobDef MPA_RemoveArmorModule;
        public static JobDef MPA_Longjump;

        static MPA_DefOf()
        {
            DefOfHelper.EnsureInitializedInCtor(typeof(MPA_DefOf));
        }
    }
}
