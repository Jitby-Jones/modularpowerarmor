using System.Collections.Generic;
using System.Linq;
using RimWorld;
using Verse;
using Verse.AI;

namespace ModularPowerArmor
{
    /// <summary>Float menu options for installing and removing modifications.</summary>
    public static class ArmorModuleMenus
    {
        /// <summary>The "Modify armor" gizmo: the pawn works on the armor it is wearing.</summary>
        public static List<FloatMenuOption> WornArmorOptions(Pawn pawn)
        {
            List<FloatMenuOption> options = new List<FloatMenuOption>();
            List<Thing> available = ArmorModuleUtility.AvailableModulesFor(pawn);
            foreach (CompModularArmor armor in ArmorModuleUtility.WornModularArmor(pawn))
            {
                options.AddRange(OptionsFor(pawn, armor, available));
            }
            if (options.Count == 0)
            {
                options.Add(new FloatMenuOption("MPA_NothingToInstall".Translate(), null));
            }
            return options;
        }

        /// <summary>Right-clicking unworn modular armor on the map with a colonist selected.</summary>
        public static IEnumerable<FloatMenuOption> GroundArmorOptions(Pawn pawn, CompModularArmor armor)
        {
            if (!pawn.IsColonistPlayerControlled)
            {
                yield break;
            }
            if (!pawn.CanReach(armor.parent, PathEndMode.Touch, Danger.Deadly))
            {
                yield return new FloatMenuOption("MPA_ModifyArmorOption".Translate(armor.parent.LabelShort) + ": " + "NoPath".Translate().CapitalizeFirst(), null);
                yield break;
            }
            if (armor.parent.IsForbidden(pawn))
            {
                yield break;
            }
            foreach (FloatMenuOption option in OptionsFor(pawn, armor, ArmorModuleUtility.AvailableModulesFor(pawn)))
            {
                yield return option;
            }
        }

        /// <summary>Right-clicking a modification item: install it into armor the pawn is wearing.</summary>
        public static IEnumerable<FloatMenuOption> InstallIntoWornArmorOptions(Pawn pawn, Thing module)
        {
            if (!pawn.IsColonistPlayerControlled || !module.Spawned)
            {
                yield break;
            }
            CompProperties_ArmorModule props = ArmorModuleUtility.PropsOf(module);
            if (props == null)
            {
                yield break;
            }
            foreach (CompModularArmor armor in ArmorModuleUtility.WornModularArmor(pawn))
            {
                if (!props.FitsSlot(armor.Slot))
                {
                    continue;
                }
                string label = "MPA_InstallOption".Translate(module.LabelNoCount, armor.parent.LabelShort);
                AcceptanceReport report = ArmorModuleUtility.CanWorkOnArmor(pawn);
                if (report.Accepted)
                {
                    report = armor.CanInstall(module);
                }
                if (report.Accepted && !pawn.CanReserveAndReach(module, PathEndMode.ClosestTouch, Danger.Deadly))
                {
                    report = "NoPath".Translate().CapitalizeFirst().Resolve();
                }
                yield return MakeOption(label, report, () => OrderInstall(pawn, module, armor), module.def);
            }
        }

        private static IEnumerable<FloatMenuOption> OptionsFor(Pawn pawn, CompModularArmor armor, List<Thing> available)
        {
            AcceptanceReport capable = ArmorModuleUtility.CanWorkOnArmor(pawn);
            foreach (Thing module in armor.Modules.ToList())
            {
                string label = "MPA_RemoveOption".Translate(module.LabelNoCount, armor.parent.LabelShort);
                AcceptanceReport report = capable.Accepted ? armor.CanRemove(module) : capable;
                yield return MakeOption(label, report, () => OrderRemove(pawn, armor, module), module.def);
            }
            foreach (Thing module in available)
            {
                if (!ArmorModuleUtility.PropsOf(module).FitsSlot(armor.Slot))
                {
                    continue;
                }
                string label = "MPA_InstallOption".Translate(module.LabelNoCount, armor.parent.LabelShort);
                AcceptanceReport report = capable.Accepted ? armor.CanInstall(module) : capable;
                yield return MakeOption(label, report, () => OrderInstall(pawn, module, armor), module.def);
            }
        }

        private static FloatMenuOption MakeOption(string label, AcceptanceReport report, System.Action action, ThingDef icon)
        {
            if (!report.Accepted)
            {
                string reason = report.Reason.NullOrEmpty() ? "" : ": " + report.Reason;
                return new FloatMenuOption(label + reason, null, icon);
            }
            return new FloatMenuOption(label, action, icon);
        }

        public static void OrderInstall(Pawn pawn, Thing module, CompModularArmor armor)
        {
            Job job = JobMaker.MakeJob(MPA_DefOf.MPA_InstallArmorModule, module, armor.parent, ProgressTarget(pawn, armor));
            job.count = 1;
            pawn.jobs.TryTakeOrderedJob(job, JobTag.Misc);
        }

        public static void OrderRemove(Pawn pawn, CompModularArmor armor, Thing module)
        {
            Job job = JobMaker.MakeJob(MPA_DefOf.MPA_RemoveArmorModule, armor.parent, module, ProgressTarget(pawn, armor));
            pawn.jobs.TryTakeOrderedJob(job, JobTag.Misc);
        }

        // Worn armor isn't on the map, so its progress bar is drawn over the wearer instead.
        private static LocalTargetInfo ProgressTarget(Pawn pawn, CompModularArmor armor)
        {
            return armor.Wearer == pawn ? (LocalTargetInfo)pawn : LocalTargetInfo.Invalid;
        }
    }
}
