using System.Collections.Generic;
using RimWorld;
using Verse;
using Verse.AI;

namespace ModularPowerArmor
{
    /// <summary>
    /// A: the armor (on the map, or worn by the actor), B: the installed modification,
    /// C: the Armor Modulus the actor works at when the armor is worn.
    /// </summary>
    public class JobDriver_RemoveArmorModule : JobDriver
    {
        private const TargetIndex ArmorInd = TargetIndex.A;
        private const TargetIndex ModuleInd = TargetIndex.B;
        private const TargetIndex StationInd = TargetIndex.C;

        private Thing Armor => job.GetTarget(ArmorInd).Thing;

        private Thing Module => job.GetTarget(ModuleInd).Thing;

        private Building_ArmorModulus Station => job.GetTarget(StationInd).Thing as Building_ArmorModulus;

        private CompModularArmor ArmorComp => Armor?.TryGetComp<CompModularArmor>();

        private bool ArmorWornByActor => (Armor as Apparel)?.Wearer == pawn;

        public override bool TryMakePreToilReservations(bool errorOnFailed)
        {
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
            else
            {
                // Armor someone is wearing can only be modified at an Armor Modulus.
                this.FailOn(() => Station == null || Station.Destroyed || !Station.CurrentlyUsableForBills());
                this.FailOnForbidden(StationInd);
                yield return Toils_Goto.GotoThing(StationInd, PathEndMode.InteractionCell);
            }

            Toil work = Toils_General.Wait(ArmorModuleUtility.WorkTicks(pawn, Module));
            work.WithProgressBarToilDelay(armorOnMap ? ArmorInd : StationInd);
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
