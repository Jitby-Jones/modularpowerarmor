using Verse;

namespace ModularPowerArmor
{
    /// <summary>
    /// Applies the combined wearer effects of every modification on the armor a pawn is wearing.
    /// The stage is rebuilt from the worn armor whenever modules, quality or implants change, so
    /// effects show up in the health tab and in stat breakdowns like any other hediff.
    /// </summary>
    public class Hediff_ArmorModifications : Hediff
    {
        // Apparel removal isn't reliably reported to apparel comps, so check the worn armor regularly.
        private const int ValidateInterval = 120;

        [Unsaved] private HediffStage stage;
        [Unsaved] private bool dirty = true;
        [Unsaved] private int lastSignature;
        [Unsaved] private bool pendingRemoval;

        public override HediffStage CurStage
        {
            get
            {
                if (dirty || stage == null)
                {
                    Recalculate();
                }
                return stage;
            }
        }

        public override bool ShouldRemove => pendingRemoval || base.ShouldRemove;

        public override string LabelInBrackets
        {
            get
            {
                int count = ArmorModuleUtility.InstalledModuleCount(pawn);
                return count > 0 ? "MPA_HediffModuleCount".Translate(count).Resolve() : base.LabelInBrackets;
            }
        }

        public override string TipStringExtra
        {
            get
            {
                string modules = ArmorModuleUtility.WornModulesDescription(pawn);
                string baseTip = base.TipStringExtra;
                return baseTip.NullOrEmpty() ? modules : baseTip + "\n" + modules;
            }
        }

        public void SetDirty()
        {
            dirty = true;
            pendingRemoval = false;
        }

        private void Recalculate()
        {
            dirty = false;
            stage = ArmorModuleUtility.BuildWearerStage(pawn);
            lastSignature = ArmorModuleUtility.WornSignature(pawn);
        }

#if RW_1_5
        public override void Tick()
        {
            base.Tick();
            if (pawn.IsHashIntervalTick(ValidateInterval))
            {
                Validate();
            }
        }
#else
        public override void TickInterval(int delta)
        {
            base.TickInterval(delta);
            if (pawn.IsHashIntervalTick(ValidateInterval, delta))
            {
                Validate();
            }
        }
#endif

        /// <summary>
        /// Catches changes this hediff isn't told about directly, such as an implant being installed
        /// (bionic synchronization) or the armor being taken off by something that skips the usual notifications.
        /// </summary>
        private void Validate()
        {
            pendingRemoval = !ArmorModuleUtility.HasWearerEffects(pawn);
            if (pendingRemoval)
            {
                return;
            }
            if (ArmorModuleUtility.WornSignature(pawn) != lastSignature)
            {
                dirty = true;
                pawn.health.Notify_HediffChanged(this);
            }
        }
    }
}
