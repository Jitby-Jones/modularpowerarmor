using System.Collections.Generic;
using RimWorld;
using Verse;
using Verse.AI;

namespace ModularPowerArmor
{
    /// <summary>
    /// A: the modification item, B: the armor (on the map, or worn by the actor),
    /// C: the actor when the armor is worn (where the progress bar is drawn).
    /// </summary>
    public class JobDriver_InstallArmorModule : JobDriver
    {
        private const TargetIndex ModuleInd = TargetIndex.A;
        private const TargetIndex ArmorInd = TargetIndex.B;
        private const TargetIndex WearerInd = TargetIndex.C;

        private Thing Module => job.GetTarget(ModuleInd).Thing;

        private Thing Armor => job.GetTarget(ArmorInd).Thing;

        private CompModularArmor ArmorComp => Armor?.TryGetComp<CompModularArmor>();

        private bool ArmorWornByActor => (Armor as Apparel)?.Wearer == pawn;

        public override bool TryMakePreToilReservations(bool errorOnFailed)
        {
            if (!pawn.Reserve(Module, job, 1, 1, null, errorOnFailed))
            {
                return false;
            }
            if (Armor != null && Armor.Spawned && !pawn.Reserve(Armor, job, 1, -1, null, errorOnFailed))
            {
                return false;
            }
            return true;
        }

        protected override IEnumerable<Toil> MakeNewToils()
        {
            bool armorOnMap = Armor != null && Armor.Spawned;
            this.FailOnDestroyedOrNull(ModuleInd);
            this.FailOnDestroyedOrNull(ArmorInd);
            this.FailOn(() => ArmorComp == null || (!Armor.Spawned && !ArmorWornByActor));
            if (armorOnMap)
            {
                this.FailOnForbidden(ArmorInd);
            }
            AddFinishAction(condition =>
            {
                // Don't walk off still holding the module if the job is interrupted.
                if (condition != JobCondition.Succeeded && Module != null && pawn.carryTracker?.CarriedThing == Module && pawn.Spawned)
                {
                    pawn.carryTracker.TryDropCarriedThing(pawn.Position, ThingPlaceMode.Near, out Thing _);
                }
            });

            yield return Toils_Goto.GotoThing(ModuleInd, PathEndMode.ClosestTouch)
                .FailOnDespawnedNullOrForbidden(ModuleInd)
                .FailOnSomeonePhysicallyInteracting(ModuleInd);
            yield return Toils_Haul.StartCarryThing(ModuleInd);

            if (armorOnMap)
            {
                yield return Toils_Goto.GotoThing(ArmorInd, PathEndMode.Touch);
            }

            Toil work = Toils_General.Wait(ArmorModuleUtility.WorkTicks(pawn, Module));
            work.WithProgressBarToilDelay(armorOnMap ? ArmorInd : WearerInd);
            work.FailOn(() => pawn.carryTracker.CarriedThing != Module);
            yield return work;

            Toil finish = ToilMaker.MakeToil("MPA_FinishInstall");
            finish.initAction = () =>
            {
                CompModularArmor armor = ArmorComp;
                Thing module = pawn.carryTracker.CarriedThing;
                if (armor == null || module == null || module != Module)
                {
                    EndJobWith(JobCondition.Incompletable);
                    return;
                }
                AcceptanceReport report = armor.CanInstall(module);
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
                if (armor.TryInstall(module, pawn.carryTracker.innerContainer))
                {
                    Messages.Message("MPA_Installed".Translate(pawn.LabelShort, moduleLabel, armor.parent.LabelShort, pawn.Named("PAWN")),
                        pawn, MessageTypeDefOf.SilentInput, false);
                }
            };
            finish.defaultCompleteMode = ToilCompleteMode.Instant;
            yield return finish;
        }
    }
}
