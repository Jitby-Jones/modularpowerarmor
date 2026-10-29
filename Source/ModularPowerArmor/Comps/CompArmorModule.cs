using System.Text;
using RimWorld;
using Verse;

namespace ModularPowerArmor
{
    /// <summary>Lives on an armor modification item.</summary>
    public class CompArmorModule : ThingComp
    {
        /// <summary>A second heart that has already refused death once. It does nothing until replaced.</summary>
        public bool spent;

        /// <summary>Game tick the longjump hydraulics can leap again.</summary>
        public int longjumpReadyTick = -1;

        public CompProperties_ArmorModule Props => (CompProperties_ArmorModule)props;

        public QualityCategory Quality => parent.TryGetQuality(out QualityCategory quality) ? quality : QualityCategory.Normal;

        public int LongjumpTicksLeft => Current.Game == null ? 0 : System.Math.Max(0, longjumpReadyTick - Find.TickManager.TicksGame);

        public override string TransformLabel(string label)
        {
            return spent ? "MPA_SpentLabel".Translate(label).Resolve() : label;
        }

        public override float GetStatFactor(StatDef stat)
        {
            float factor = base.GetStatFactor(stat);
            return spent && stat == StatDefOf.MarketValue ? factor * 0.1f : factor;
        }

        public override string CompInspectStringExtra()
        {
            StringBuilder sb = new StringBuilder();
            sb.Append("MPA_InspectModule".Translate(
                ArmorModuleStatDisplay.SlotsLabel(Props),
                ArmorModuleUtility.LoadCost(parent).ToString("0.#")));
            if (spent)
            {
                sb.AppendLine();
                sb.Append("MPA_InspectSpent".Translate());
            }
            return sb.ToString();
        }

        public override void PostExposeData()
        {
            base.PostExposeData();
            Scribe_Values.Look(ref spent, "mpaSpent", false);
            Scribe_Values.Look(ref longjumpReadyTick, "mpaLongjumpReadyTick", -1);
        }
    }
}
