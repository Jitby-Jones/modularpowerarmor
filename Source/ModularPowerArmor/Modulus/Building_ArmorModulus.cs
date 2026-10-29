using System.Collections.Generic;
using RimWorld;
using UnityEngine;
using Verse;
using Verse.AI;

namespace ModularPowerArmor
{
    /// <summary>
    /// The Armor Modulus: bills modify armor in bulk, and right-clicking it with a colonist selected
    /// opens a window for modifying the armor that colonist is wearing.
    /// </summary>
    public class Building_ArmorModulus : Building_WorkTable
    {
        public AcceptanceReport CanModifyWornArmor(Pawn pawn)
        {
            if (ArmorModuleUtility.FirstWornModularArmor(pawn) == null)
            {
                return "MPA_Reason_NoModularArmor".Translate(pawn.LabelShort, pawn).Resolve();
            }
            if (!CurrentlyUsableForBills())
            {
                return "MPA_Reason_ModulusUnusable".Translate(LabelShort).Resolve();
            }
            if (this.IsForbidden(pawn))
            {
                return "ForbiddenLower".Translate().Resolve();
            }
            if (!pawn.CanReach(this, PathEndMode.InteractionCell, Danger.Deadly))
            {
                return "NoPath".Translate().CapitalizeFirst().Resolve();
            }
            return ArmorModuleUtility.CanWorkOnArmor(pawn);
        }

        public override IEnumerable<FloatMenuOption> GetFloatMenuOptions(Pawn selPawn)
        {
            foreach (FloatMenuOption option in base.GetFloatMenuOptions(selPawn))
            {
                yield return option;
            }
            if (!selPawn.IsColonistPlayerControlled)
            {
                yield break;
            }
            string label = "MPA_ModulusOption".Translate(selPawn.LabelShort, selPawn.Named("PAWN"));
            AcceptanceReport report = CanModifyWornArmor(selPawn);
            if (!report.Accepted)
            {
                yield return new FloatMenuOption(label + (report.Reason.NullOrEmpty() ? "" : ": " + report.Reason), null,
                    ArmorModuleTextures.ModifyArmor, Color.white);
                yield break;
            }
            yield return new FloatMenuOption(label, () => Find.WindowStack.Add(new Dialog_ArmorModulus(selPawn, this)),
                ArmorModuleTextures.ModifyArmor, Color.white);
        }
    }
}
