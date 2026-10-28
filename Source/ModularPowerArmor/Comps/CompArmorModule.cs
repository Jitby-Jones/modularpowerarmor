using System.Collections.Generic;
using RimWorld;
using Verse;

namespace ModularPowerArmor
{
    /// <summary>Lives on an armor modification item.</summary>
    public class CompArmorModule : ThingComp
    {
        public CompProperties_ArmorModule Props => (CompProperties_ArmorModule)props;

        public QualityCategory Quality => parent.TryGetQuality(out QualityCategory quality) ? quality : QualityCategory.Normal;

        public override IEnumerable<FloatMenuOption> CompFloatMenuOptions(Pawn selPawn)
        {
            foreach (FloatMenuOption option in base.CompFloatMenuOptions(selPawn))
            {
                yield return option;
            }
            foreach (FloatMenuOption option in ArmorModuleMenus.InstallIntoWornArmorOptions(selPawn, parent))
            {
                yield return option;
            }
        }

        public override string CompInspectStringExtra()
        {
            return "MPA_InspectModule".Translate(
                ArmorModuleStatDisplay.SlotsLabel(Props),
                ArmorModuleUtility.LoadCost(parent).ToString("0.#"));
        }
    }
}
