using System.Collections.Generic;
using System.Linq;
using RimWorld;
using UnityEngine;
using Verse;
using Verse.AI;

namespace ModularPowerArmor
{
    /// <summary>
    /// Opened from an Armor Modulus with a colonist selected: the armor the colonist is wearing, its
    /// modifications and load, the modifications they could install, and their stats. Buttons queue
    /// jobs that the colonist carries out at the station.
    /// </summary>
    public class Dialog_ArmorModulus : Window
    {
        private const float RowHeight = 30f;
        private const float IconSize = 26f;
        private const float ButtonWidth = 120f;
        private const float StatRowHeight = 24f;
        private const int AvailableRefreshFrames = 60;

        private readonly Pawn pawn;
        private readonly Building_ArmorModulus station;
        private Vector2 armorScroll;
        private Vector2 wearerScroll;
        private float armorHeight = 600f;
        private float wearerHeight = 600f;
        private List<Thing> available = new List<Thing>();
        private int availableFrame = -AvailableRefreshFrames;
        private AcceptanceReport stationReport;

        public Dialog_ArmorModulus(Pawn pawn, Building_ArmorModulus station)
        {
            this.pawn = pawn;
            this.station = station;
            doCloseX = true;
            doCloseButton = true;
            closeOnClickedOutside = true;
            absorbInputAroundWindow = true;
        }

        public override Vector2 InitialSize => new Vector2(1000f, 720f);

        public override void DoWindowContents(Rect inRect)
        {
            if (station.Destroyed || pawn.Dead || pawn.MapHeld != station.Map)
            {
                Close();
                return;
            }
            stationReport = station.CanModifyWornArmor(pawn);
            Text.Font = GameFont.Medium;
            Rect title = new Rect(inRect.x, inRect.y, inRect.width - 40f, 36f);
            Widgets.Label(title, "MPA_ModulusTitle".Translate(pawn.LabelShort, station.LabelCap, pawn.Named("PAWN")));
            Text.Font = GameFont.Small;
            GUI.color = Color.gray;
            Widgets.Label(new Rect(inRect.x, title.yMax, inRect.width, 24f), "MPA_ModulusSubtitle".Translate(pawn.LabelShort, pawn.Named("PAWN")));
            GUI.color = Color.white;

            float top = title.yMax + 30f;
            float bottom = inRect.yMax - CloseButSize.y - 12f;
            Rect left = new Rect(inRect.x, top, Mathf.Floor(inRect.width * 0.62f), bottom - top);
            Rect right = new Rect(left.xMax + 12f, top, inRect.xMax - left.xMax - 12f, bottom - top);
            DrawArmor(left);
            DrawWearer(right);
        }

        // ---- Armor ----

        private void DrawArmor(Rect outRect)
        {
            Widgets.DrawMenuSection(outRect);
            Rect inner = outRect.ContractedBy(8f);
            Rect view = new Rect(0f, 0f, inner.width - 16f, Mathf.Max(armorHeight, inner.height));
            if (Time.frameCount - availableFrame >= AvailableRefreshFrames)
            {
                available = ArmorModuleUtility.AvailableModulesFor(pawn);
                availableFrame = Time.frameCount;
            }
            Widgets.BeginScrollView(inner, ref armorScroll, view);
            float y = 0f;
            List<CompModularArmor> worn = ArmorModuleUtility.WornModularArmor(pawn).ToList();
            if (worn.Count == 0)
            {
                Widgets.Label(new Rect(0f, y, view.width, 30f), "MPA_Reason_NoModularArmor".Translate(pawn.LabelShort, pawn).CapitalizeFirst());
                y += 30f;
            }
            foreach (CompModularArmor armor in worn)
            {
                y = DrawPiece(armor, view.width, y);
                y += 14f;
            }
            armorHeight = y;
            Widgets.EndScrollView();
        }

        private float DrawPiece(CompModularArmor armor, float width, float y)
        {
            Thing apparel = armor.parent;
            Rect header = new Rect(0f, y, width, 40f);
            Widgets.DrawLightHighlight(header);
            Widgets.ThingIcon(new Rect(4f, y + 4f, 32f, 32f), apparel);
            Text.Anchor = TextAnchor.MiddleLeft;
            Widgets.Label(new Rect(44f, y, width - 280f, 40f), apparel.LabelCap);
            Text.Anchor = TextAnchor.UpperLeft;

            float used = armor.UsedLoad;
            float capacity = armor.Capacity;
            Rect bar = new Rect(width - 224f, y + 9f, 216f, 22f);
            Widgets.FillableBar(bar, capacity > 0f ? Mathf.Clamp01(used / capacity) : 1f, armor.IsOverloaded ? ArmorModuleTextures.OverloadBar : ArmorModuleTextures.LoadBar);
            Text.Anchor = TextAnchor.MiddleCenter;
            Widgets.Label(bar, "MPA_LoadBar".Translate(used.ToString("0.#"), capacity.ToString("0.#")));
            Text.Anchor = TextAnchor.UpperLeft;
            TooltipHandler.TipRegion(bar, MPA_DefOf.MPA_ComputationalLoad.description);
            y += 44f;

            GUI.color = Color.gray;
            Widgets.Label(new Rect(8f, y, width - 8f, 24f), ArmorStatsLine(apparel));
            GUI.color = Color.white;
            y += 24f;
            if (armor.IsOverloaded)
            {
                Rect warning = new Rect(8f, y, width - 8f, Text.CalcHeight("MPA_InspectOverloaded".Translate(), width - 8f));
                Widgets.Label(warning, "MPA_InspectOverloaded".Translate().Colorize(ColorLibrary.RedReadable));
                y += warning.height;
            }

            y = SectionLabel("MPA_ModulusInstalled".Translate(), width, y);
            if (armor.Modules.Count == 0)
            {
                y = NoneLabel(width, y);
            }
            foreach (Thing module in armor.Modules.ToList())
            {
                string detail = ModuleDetail(module, armor.EffectMultiplier(module), true);
                AcceptanceReport report = IsQueued(module) ? "MPA_Queued".Translate().Resolve() : RemoveReport(armor, module);
                string button = IsQueued(module) ? "MPA_Queued".Translate().CapitalizeFirst() : "MPA_ModulusRemove".Translate().CapitalizeFirst();
                Thing target = module;
                y = ModuleRow(y, width, module, detail, button, report, () => ArmorModuleMenus.OrderRemove(pawn, armor, target, station, AlreadyBusyHere()));
            }

            y = SectionLabel("MPA_ModulusAvailable".Translate(), width, y);
            bool any = false;
            foreach (Thing module in available)
            {
                CompProperties_ArmorModule props = ArmorModuleUtility.PropsOf(module);
                if (props == null || !props.FitsSlot(armor.Slot) || module.Destroyed || !module.Spawned)
                {
                    continue;
                }
                any = true;
                bool queued = IsQueued(module);
                string detail = ModuleDetail(module, ArmorModuleUtility.QualityMultiplier(module), false);
                AcceptanceReport report = queued ? "MPA_Queued".Translate().Resolve() : InstallReport(armor, module);
                string button = queued ? "MPA_Queued".Translate().CapitalizeFirst() : "MPA_ModulusInstall".Translate().CapitalizeFirst();
                Thing target = module;
                y = ModuleRow(y, width, module, detail, button, report, () =>
                {
                    ArmorModuleMenus.OrderInstall(pawn, target, armor, station, AlreadyBusyHere());
                    availableFrame = -AvailableRefreshFrames;
                });
            }
            if (!any)
            {
                y = NoneLabel(width, y);
            }
            return y;
        }

        private AcceptanceReport InstallReport(CompModularArmor armor, Thing module)
        {
            return stationReport.Accepted ? armor.CanInstall(module) : stationReport;
        }

        private AcceptanceReport RemoveReport(CompModularArmor armor, Thing module)
        {
            return stationReport.Accepted ? armor.CanRemove(module) : stationReport;
        }

        private static string ModuleDetail(Thing module, float strength, bool installed)
        {
            string load = "MPA_ModulusLoadCost".Translate(ArmorModuleUtility.LoadCost(module).ToString("0.#"));
            if (!ArmorModuleUtility.HasQuality(module.def))
            {
                return load;
            }
            return installed ? load + ", " + "MPA_Stat_EffectStrength".Translate(strength.ToStringPercent()) : load;
        }

        private static string ArmorStatsLine(Thing apparel)
        {
            StatDef[] stats = { StatDefOf.ArmorRating_Sharp, StatDefOf.ArmorRating_Blunt, StatDefOf.ArmorRating_Heat };
            return string.Join("   ", stats.Select(s => s.LabelCap + ": " + s.ValueToString(apparel.GetStatValue(s))));
        }

        private float ModuleRow(float y, float width, Thing module, string detail, string buttonLabel, AcceptanceReport report, System.Action onClick)
        {
            Rect row = new Rect(0f, y, width, RowHeight);
            Widgets.DrawHighlightIfMouseover(row);
            Widgets.ThingIcon(new Rect(8f, y + 2f, IconSize, IconSize), module);
            Rect label = new Rect(8f + IconSize + 8f, y, width - ButtonWidth - IconSize - 28f, RowHeight);
            Text.Anchor = TextAnchor.MiddleLeft;
            Widgets.Label(label, module.LabelCapNoCount + "  " + detail.Colorize(Color.gray));
            Text.Anchor = TextAnchor.UpperLeft;
            TooltipHandler.TipRegion(label, module.DescriptionDetailed);
            Rect button = new Rect(width - ButtonWidth, y + 2f, ButtonWidth, RowHeight - 4f);
            if (Widgets.ButtonText(button, buttonLabel, active: report.Accepted) && report.Accepted)
            {
                onClick();
            }
            if (!report.Accepted && !report.Reason.NullOrEmpty())
            {
                TooltipHandler.TipRegion(button, report.Reason.CapitalizeFirst());
            }
            return y + RowHeight;
        }

        private static float SectionLabel(string label, float width, float y)
        {
            y += 4f;
            Widgets.Label(new Rect(4f, y, width - 4f, 24f), label);
            Widgets.DrawLineHorizontal(4f, y + 22f, width - 4f);
            return y + 26f;
        }

        private static float NoneLabel(float width, float y)
        {
            GUI.color = Color.gray;
            Widgets.Label(new Rect(12f, y, width - 12f, 24f), "MPA_ModulusNone".Translate());
            GUI.color = Color.white;
            return y + 24f;
        }

        private bool IsQueued(Thing module)
        {
            if (Targets(pawn.CurJob, module))
            {
                return true;
            }
            foreach (QueuedJob queued in pawn.jobs.jobQueue)
            {
                if (Targets(queued.job, module))
                {
                    return true;
                }
            }
            return false;
        }

        private static bool Targets(Job job, Thing module)
        {
            return job != null
                && (job.def == MPA_DefOf.MPA_InstallArmorModule || job.def == MPA_DefOf.MPA_RemoveArmorModule)
                && (job.targetA.Thing == module || job.targetB.Thing == module);
        }

        /// <summary>Queue behind modulus work the pawn is already doing instead of interrupting it.</summary>
        private bool AlreadyBusyHere()
        {
            if (pawn.CurJobDef == MPA_DefOf.MPA_InstallArmorModule || pawn.CurJobDef == MPA_DefOf.MPA_RemoveArmorModule)
            {
                return true;
            }
            foreach (QueuedJob queued in pawn.jobs.jobQueue)
            {
                if (queued.job.def == MPA_DefOf.MPA_InstallArmorModule || queued.job.def == MPA_DefOf.MPA_RemoveArmorModule)
                {
                    return true;
                }
            }
            return false;
        }

        // ---- Wearer ----

        private void DrawWearer(Rect outRect)
        {
            Widgets.DrawMenuSection(outRect);
            Rect inner = outRect.ContractedBy(8f);
            Rect view = new Rect(0f, 0f, inner.width - 16f, Mathf.Max(wearerHeight, inner.height));
            Widgets.BeginScrollView(inner, ref wearerScroll, view);
            float y = SectionLabel("MPA_ModulusWearer".Translate(pawn.LabelShort, pawn.Named("PAWN")), view.width, 0f);
            foreach ((string label, string value, string tip) in WearerStats())
            {
                Rect row = new Rect(0f, y, view.width, StatRowHeight);
                Widgets.DrawHighlightIfMouseover(row);
                Text.Anchor = TextAnchor.MiddleLeft;
                Widgets.Label(new Rect(6f, y, view.width * 0.62f, StatRowHeight), label);
                Text.Anchor = TextAnchor.MiddleRight;
                Widgets.Label(new Rect(view.width * 0.62f, y, view.width * 0.38f - 6f, StatRowHeight), value);
                Text.Anchor = TextAnchor.UpperLeft;
                if (!tip.NullOrEmpty())
                {
                    TooltipHandler.TipRegion(row, tip);
                }
                y += StatRowHeight;
            }

            y = SectionLabel("MPA_ModulusEffects".Translate(), view.width, y + 6f);
            List<string> lines = ArmorModuleUtility.SpecialEffectLines(pawn);
            if (lines.Count == 0)
            {
                y = NoneLabel(view.width, y);
            }
            foreach (string line in lines)
            {
                string text = "- " + line;
                float height = Text.CalcHeight(text, view.width - 6f);
                Widgets.Label(new Rect(6f, y, view.width - 6f, height), text);
                y += height + 2f;
            }
            wearerHeight = y;
            Widgets.EndScrollView();
        }

        private IEnumerable<(string label, string value, string tip)> WearerStats()
        {
            yield return Stat(StatDefOf.MoveSpeed);
            yield return Capacity(PawnCapacityDefOf.Manipulation);
            yield return Capacity(PawnCapacityDefOf.Consciousness);
            yield return Capacity(PawnCapacityDefOf.Sight);
            yield return ("MPA_ModulusPain".Translate().CapitalizeFirst(), pawn.health.hediffSet.PainTotal.ToStringPercent(), "");
            yield return Stat(StatDefOf.IncomingDamageFactor);
            yield return Stat(StatDefOf.MentalBreakThreshold);
            yield return Stat(StatDefOf.AimingDelayFactor);
            yield return Stat(StatDefOf.MeleeDamageFactor);
            yield return Stat(StatDefOf.CarryingCapacity);
            yield return Stat(StatDefOf.ComfyTemperatureMin);
            yield return Stat(StatDefOf.ComfyTemperatureMax);
            // Combat Extended
            foreach (string name in new[] { "Suppressability", "AimingAccuracy" })
            {
                StatDef stat = DefDatabase<StatDef>.GetNamedSilentFail(name);
                if (stat != null)
                {
                    yield return Stat(stat);
                }
            }
        }

        private (string, string, string) Stat(StatDef stat)
        {
            return (stat.LabelCap, stat.ValueToString(pawn.GetStatValue(stat)), stat.description);
        }

        private (string, string, string) Capacity(PawnCapacityDef capacity)
        {
            return (capacity.GetLabelFor(pawn).CapitalizeFirst(), pawn.health.capacities.GetLevel(capacity).ToStringPercent(), capacity.description);
        }
    }
}
