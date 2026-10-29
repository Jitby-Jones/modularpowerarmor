using System.Collections.Generic;
using System.Linq;
using RimWorld;
using Verse;
using Verse.AI;

namespace ModularPowerArmor
{
    /// <summary>
    /// Installing and removing modifications by hand. Armor lying on the map is worked on where it
    /// lies; armor someone is wearing only at an Armor Modulus (see <see cref="Dialog_ArmorModulus"/>).
    /// </summary>
    public static class ArmorModuleMenus
    {
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

        /// <summary>Installs a module, into armor on the map or, with a station, into armor the pawn is wearing.</summary>
        public static void OrderInstall(Pawn pawn, Thing module, CompModularArmor armor, Building_ArmorModulus station = null, bool queue = false)
        {
            Job job = JobMaker.MakeJob(MPA_DefOf.MPA_InstallArmorModule, module, armor.parent, station);
            job.count = 1;
            pawn.jobs.TryTakeOrderedJob(job, JobTag.Misc, queue);
        }

        /// <summary>Removes a module from armor on the map or, with a station, from armor the pawn is wearing.</summary>
        public static void OrderRemove(Pawn pawn, CompModularArmor armor, Thing module, Building_ArmorModulus station = null, bool queue = false)
        {
            Job job = JobMaker.MakeJob(MPA_DefOf.MPA_RemoveArmorModule, armor.parent, module, station);
            pawn.jobs.TryTakeOrderedJob(job, JobTag.Misc, queue);
        }
    }
}
