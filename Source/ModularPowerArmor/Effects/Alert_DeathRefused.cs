using System.Collections.Generic;
using System.Text;
using RimWorld;
using Verse;

namespace ModularPowerArmor
{
    /// <summary>
    /// Red (critical) alert for every pawn a second heart is keeping alive, with the blow that took
    /// their head. Like other critical alerts it also posts a message when it goes up.
    /// </summary>
    public class Alert_DeathRefused : Alert_Critical
    {
        private readonly List<Pawn> sustained = new List<Pawn>();

        private List<Pawn> SustainedPawns
        {
            get
            {
                sustained.Clear();
#if RW_1_5
                List<Pawn> pawns = PawnsFinder.AllMapsCaravansAndTravelingTransportPods_Alive_OfPlayerFaction;
#else
                List<Pawn> pawns = PawnsFinder.AllMapsCaravansAndTravellingTransporters_Alive_OfPlayerFaction;
#endif
                for (int i = 0; i < pawns.Count; i++)
                {
                    if (DeathRefusalUtility.IsSustained(pawns[i]))
                    {
                        sustained.Add(pawns[i]);
                    }
                }
                return sustained;
            }
        }

        public override string GetLabel()
        {
            List<Pawn> pawns = SustainedPawns;
            if (pawns.Count == 1)
            {
                return "MPA_DeathRefusedAlert".Translate(pawns[0].LabelShort, pawns[0].Named("PAWN")).Resolve();
            }
            return "MPA_DeathRefusedAlertMulti".Translate(pawns.Count).Resolve();
        }

        public override TaggedString GetExplanation()
        {
            StringBuilder sb = new StringBuilder();
            foreach (Pawn pawn in SustainedPawns)
            {
                if (!(pawn.health.hediffSet.GetFirstHediffOfDef(MPA_DefOf.MPA_DeathRefused) is Hediff_DeathRefused hediff))
                {
                    continue;
                }
                if (sb.Length > 0)
                {
                    sb.AppendLine().AppendLine();
                }
                sb.Append("MPA_DeathRefusedAlertDesc".Translate(
                    pawn.LabelShort,
                    hediff.killingBlow.NullOrEmpty() ? "MPA_KillingBlowUnknown".Translate().Resolve() : hediff.killingBlow,
                    hediff.ticksLeft.ToStringTicksToPeriod(allowSeconds: false),
                    pawn.Named("PAWN")).Resolve());
            }
            return sb.ToString();
        }

        public override AlertReport GetReport()
        {
            return AlertReport.CulpritsAre(SustainedPawns);
        }
    }
}
