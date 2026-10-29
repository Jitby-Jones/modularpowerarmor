using System.Collections.Generic;
using RimWorld;
using Verse;
using Verse.AI;

namespace ModularPowerArmor
{
    /// <summary>
    /// A: the modification item, B: the armor (on the map, or worn by the actor),
    /// C: the Armor Modulus the actor works at when the armor is worn.
    /// </summary>
    public class JobDriver_InstallArmorModule : JobDriver
    {
        private const TargetIndex ModuleInd = TargetIndex.A;
        private const TargetIndex ArmorInd = TargetIndex.B;
        private const TargetIndex StationInd = TargetIndex.C;

        private Thing Module => job.GetTarget(ModuleInd).Thing;

        private Thing Armor => job.GetTarget(ArmorInd).Thing;

        private Building_ArmorModulus Station => job.GetTarget(StationInd).Thing as Building_ArmorModulus;

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
            if (Station != null && !pawn.Reserve(Station, job, 1, -1, null, errorOnFailed))
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
            else
            {
                // Armor someone is wearing can only be modified at an Armor Modulus.
                this.FailOn(() => Station == null || Station.Destroyed || !Station.CurrentlyUsableForBills());
                this.FailOnForbidden(StationInd);
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

            yield return armorOnMap
                ? Toils_Goto.GotoThing(ArmorInd, PathEndMode.Touch)
                : Toils_Goto.GotoThing(StationInd, PathEndMode.InteractionCell);

            Toil work = Toils_General.Wait(ArmorModuleUtility.WorkTicks(pawn, Module));
            work.WithProgressBarToilDelay(armorOnMap ? ArmorInd : StationInd);
            work.FailOn(() => pawn.carryTracker.CarriedThing != Module);
            if (!armorOnMap)
            {
                System.Action stop = work.initAction;
                work.initAction = () =>
                {
                    stop?.Invoke();
                    pawn.rotationTracker.FaceTarget(Station);
                };
                work.WithEffect(EffecterDefOf.ConstructMetal, StationInd);
            }
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
