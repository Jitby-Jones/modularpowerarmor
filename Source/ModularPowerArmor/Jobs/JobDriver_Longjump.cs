using System.Collections.Generic;
using Verse;
using Verse.AI;

namespace ModularPowerArmor
{
    /// <summary>A: the landing cell, B: the longjump hydraulics module in the actor's worn armor.</summary>
    public class JobDriver_Longjump : JobDriver
    {
        private IntVec3 Cell => job.GetTarget(TargetIndex.A).Cell;

        private Thing Module => job.GetTarget(TargetIndex.B).Thing;

        private CompModularArmor Armor
        {
            get
            {
                Thing module = Module;
                foreach (CompModularArmor armor in ArmorModuleUtility.WornModularArmor(pawn))
                {
                    if (armor.Modules.Contains(module))
                    {
                        return armor;
                    }
                }
                return null;
            }
        }

        public override bool TryMakePreToilReservations(bool errorOnFailed)
        {
            return true;
        }

        protected override IEnumerable<Toil> MakeNewToils()
        {
            this.FailOn(() => Module == null || !LongjumpUtility.CanJumpNow(pawn, Armor, Module).Accepted);

            Toil warmup = Toils_General.Wait(LongjumpUtility.WarmupTicks);
            System.Action stop = warmup.initAction;
            warmup.initAction = () =>
            {
                stop?.Invoke();
                pawn.rotationTracker.FaceCell(Cell);
            };
            EffecterDef warmupEffect = DefDatabase<EffecterDef>.GetNamedSilentFail("JumpWarmupEffect");
            if (warmupEffect != null)
            {
                warmup.WithEffect(warmupEffect, () => (LocalTargetInfo)pawn);
            }
            yield return warmup;

            Toil leap = ToilMaker.MakeToil("MPA_Longjump");
            leap.initAction = () =>
            {
                // Launching despawns the pawn into a flyer, which ends this job.
                if (!LongjumpUtility.DoJump(pawn, Armor, Module, Cell))
                {
                    EndJobWith(JobCondition.Incompletable);
                }
            };
            leap.defaultCompleteMode = ToilCompleteMode.Instant;
            yield return leap;
        }
    }
}
