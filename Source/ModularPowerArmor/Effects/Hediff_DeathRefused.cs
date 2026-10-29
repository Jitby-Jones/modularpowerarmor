using RimWorld;
using Verse;

namespace ModularPowerArmor
{
    /// <summary>
    /// A second heart refused this pawn's death when their head was destroyed. While it lasts the
    /// pawn is held at <see cref="SustainedConsciousness"/> consciousness (see
    /// <see cref="HarmonyPatches"/>), and the first hours bring a surge of speed. Two days later
    /// they die, unless the head has been restored by then.
    /// </summary>
    public class Hediff_DeathRefused : HediffWithComps
    {
        public const int DurationTicks = 2 * GenDate.TicksPerDay;
        public const int SurgeTicks = 12 * GenDate.TicksPerHour;
        public const float SustainedConsciousness = 0.5f;
        private const int CheckInterval = 60;

        public int ticksLeft = DurationTicks;

        /// <summary>What destroyed the head, for the alert.</summary>
        public string killingBlow;

        public bool Surging => ageTicks < SurgeTicks;

        public override int CurStageIndex => def.stages == null || def.stages.Count < 2 || Surging ? 0 : 1;

        public override string LabelInBrackets => ticksLeft.ToStringTicksToPeriod(allowSeconds: false, shortForm: true);

        public override string TipStringExtra
        {
            get
            {
                string text = "MPA_DeathRefusedTip".Translate(ticksLeft.ToStringTicksToPeriod(allowSeconds: false)).Resolve();
                string baseTip = base.TipStringExtra;
                return baseTip.NullOrEmpty() ? text : baseTip + "\n" + text;
            }
        }

#if RW_1_5
        public override void Tick()
        {
            base.Tick();
            if (pawn.IsHashIntervalTick(CheckInterval))
            {
                Advance(CheckInterval);
            }
        }
#else
        public override void TickInterval(int delta)
        {
            base.TickInterval(delta);
            if (pawn.IsHashIntervalTick(CheckInterval, delta))
            {
                Advance(CheckInterval);
            }
        }
#endif

        private void Advance(int ticks)
        {
            if (pawn.Dead)
            {
                return;
            }
            bool wasSurging = ageTicks - ticks < SurgeTicks;
            if (wasSurging && !Surging)
            {
                pawn.health.Notify_HediffChanged(this);
            }
            if (DeathRefusalUtility.HeadRestored(pawn))
            {
                pawn.health.RemoveHediff(this);
                if (pawn.Faction == Faction.OfPlayer)
                {
                    Messages.Message("MPA_DeathRefusedRecovered".Translate(pawn.LabelShort, pawn.Named("PAWN")), pawn, MessageTypeDefOf.PositiveEvent);
                }
                return;
            }
            ticksLeft -= ticks;
            if (ticksLeft <= 0)
            {
                pawn.Kill(null, this);
            }
        }

        public override void ExposeData()
        {
            base.ExposeData();
            Scribe_Values.Look(ref ticksLeft, "ticksLeft", DurationTicks);
            Scribe_Values.Look(ref killingBlow, "killingBlow");
        }
    }
}
