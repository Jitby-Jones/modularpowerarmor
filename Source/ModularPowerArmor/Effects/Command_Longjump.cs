using RimWorld;
using UnityEngine;
using Verse;

namespace ModularPowerArmor
{
    /// <summary>The wearer's longjump button, with a recharge overlay like an ability's.</summary>
    public class Command_Longjump : Command_Action
    {
        private readonly CompModularArmor armor;
        private readonly Thing module;

        public Command_Longjump(Pawn pawn, CompModularArmor armor, Thing module)
        {
            this.armor = armor;
            this.module = module;
            float range = LongjumpUtility.Range(armor, module);
            int cooldown = LongjumpUtility.CooldownTicks(armor, module);
            defaultLabel = "MPA_Longjump".Translate();
            defaultDesc = "MPA_LongjumpDesc".Translate(range.ToString("0.#"), cooldown.ToStringTicksToPeriod(allowSeconds: false));
            icon = module.def.uiIcon;
            // Each pawn leaps on its own; grouping would start one targeter per selected pawn at once.
            groupable = false;
            action = () => LongjumpUtility.BeginTargeting(pawn, armor, module);
            AcceptanceReport report = LongjumpUtility.CanJumpNow(pawn, armor, module);
            if (!report.Accepted)
            {
                Disable(report.Reason);
            }
        }

        public override GizmoResult GizmoOnGUI(Vector2 topLeft, float maxWidth, GizmoRenderParms parms)
        {
            GizmoResult result = base.GizmoOnGUI(topLeft, maxWidth, parms);
            CompArmorModule comp = module.TryGetComp<CompArmorModule>();
            int left = comp?.LongjumpTicksLeft ?? 0;
            int total = LongjumpUtility.CooldownTicks(armor, module);
            if (left > 0 && total > 0)
            {
                Rect rect = new Rect(topLeft.x, topLeft.y, GetWidth(maxWidth), 75f);
                Widgets.FillableBar(rect, Mathf.Clamp01(1f - (float)left / total), ArmorModuleTextures.CooldownBar, null, false);
                Text.Font = GameFont.Tiny;
                Text.Anchor = TextAnchor.UpperCenter;
                Widgets.Label(rect, left.ToStringTicksToPeriod(allowSeconds: false, shortForm: true));
                Text.Anchor = TextAnchor.UpperLeft;
                Text.Font = GameFont.Small;
            }
            return result;
        }
    }
}
