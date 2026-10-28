using System.Collections.Generic;
using RimWorld;
using Verse;
using Verse.AI;

namespace ModularPowerArmor
{
    /// <summary>
    /// A: the armor (on the map, or worn by the actor), B: the installed modification,
    /// C: the actor when the armor is worn (where the progress bar is drawn).
    /// </summary>
    public class JobDriver_RemoveArmorModule : JobDriver
    {
        private const TargetIndex ArmorInd = TargetIndex.A;
        private const TargetIndex ModuleInd = TargetIndex.B;
        private const TargetIndex WearerInd = TargetIndex.C;

        private Thing Armor => job.GetTarget(ArmorInd).Thing;

        private Thing Module => job.GetTarget(ModuleInd).Thing;

        private CompModularArmor ArmorComp => Armor?.TryGetComp<CompModularArmor>();

        private bool ArmorWornByActor => (Armor as Apparel)?.Wearer == pawn;

        public override bool TryMakePreToilReservations(bool errorOnFailed)
        {
            return Armor == null || !Armor.Spawned || pawn.Reserve(Armor, job, 1, -1, null, errorOnFailed);
        }

        protected override IEnumerable<Toil> MakeNewToils()
        {
            bool armorOnMap = Armor != null && Armor.Spawned;
            this.FailOnDestroyedOrNull(ArmorInd);
            this.FailOn(() => ArmorComp == null
                || (!Armor.Spawned && !ArmorWornByActor)
                || Module == null
                || !ArmorComp.Modules.Contains(Module));
            if (armorOnMap)
            {
                this.FailOnForbidden(ArmorInd);
                yield return Toils_Goto.GotoThing(ArmorInd, PathEndMode.Touch);
            }

            Toil work = Toils_General.Wait(ArmorModuleUtility.WorkTicks(pawn, Module));
            work.WithProgressBarToilDelay(armorOnMap ? ArmorInd : WearerInd);
            yield return work;

            Toil finish = ToilMaker.MakeToil("MPA_FinishRemove");
            finish.initAction = () =>
            {
                CompModularArmor armor = ArmorComp;
                Thing module = Module;
                if (armor == null || module == null)
                {
                    EndJobWith(JobCondition.Incompletable);
                    return;
                }
                AcceptanceReport report = armor.CanRemove(module);
                if (!report.Accepted)
                {
                    if (!report.Reason.NullOrEmpty())
                    {
                        Messages.Message(report.Reason, pawn, MessageTypeDefOf.RejectInput, false);
                    }
                    EndJobWith(JobCondition.Incompletable);
                    return;
                }
                string moduleLabel = module.LabelNoCount;
                if (armor.TryRemove(module, pawn.Position, pawn.Map) != null)
                {
                    Messages.Message("MPA_Removed".Translate(pawn.LabelShort, moduleLabel, armor.parent.LabelShort, pawn.Named("PAWN")),
                        pawn, MessageTypeDefOf.SilentInput, false);
                }
            };
            finish.defaultCompleteMode = ToilCompleteMode.Instant;
            yield return finish;
        }
    }
}
