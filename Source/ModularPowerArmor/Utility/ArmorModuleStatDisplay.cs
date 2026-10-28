using System.Collections.Generic;
using RimWorld;
using Verse;

namespace ModularPowerArmor
{
    /// <summary>Info card entries describing a modification's effects at a given quality.</summary>
    public static class ArmorModuleStatDisplay
    {
        public static string SlotLabel(ArmorSlot slot)
        {
            return slot == ArmorSlot.Helmet ? "MPA_Slot_Helmet".Translate() : "MPA_Slot_Body".Translate();
        }

        public static string SlotsLabel(CompProperties_ArmorModule props)
        {
            bool body = props.FitsSlot(ArmorSlot.Body);
            bool helmet = props.FitsSlot(ArmorSlot.Helmet);
            if (body && helmet)
            {
                return "MPA_Slot_Universal".Translate();
            }
            return helmet ? "MPA_Slot_HelmetOnly".Translate() : "MPA_Slot_BodyOnly".Translate();
        }

        public static IEnumerable<StatDrawEntry> EntriesFor(CompProperties_ArmorModule props, QualityCategory quality)
        {
            StatCategoryDef category = MPA_DefOf.MPA_ArmorModification;
            float multiplier = ArmorModuleUtility.QualityMultiplier(quality);
            int priority = 5000;

            yield return new StatDrawEntry(category, "MPA_Stat_Fits".Translate(), SlotsLabel(props),
                "MPA_Stat_FitsDesc".Translate(), priority--);

            yield return new StatDrawEntry(category, "MPA_Stat_QualityEffect".Translate(),
                "x" + multiplier.ToStringPercent(),
                "MPA_Stat_QualityEffectDesc".Translate(quality.GetLabel(), ArmorModuleUtility.Settings.qualityStep.ToStringPercent()),
                priority--);

            if (props.wearerStatOffsets != null)
            {
                foreach (StatModifier mod in props.wearerStatOffsets)
                {
                    yield return Entry(category, "MPA_Stat_Wearer".Translate(mod.stat.label),
                        mod.stat.ValueToString(mod.value * multiplier, ToStringNumberSense.Offset), mod.stat.description, priority--);
                }
            }
            if (props.wearerStatFactors != null)
            {
                foreach (StatModifier mod in props.wearerStatFactors)
                {
                    yield return Entry(category, "MPA_Stat_Wearer".Translate(mod.stat.label),
                        "x" + ArmorModuleUtility.ScaleFactor(mod.value, multiplier).ToStringPercent(), mod.stat.description, priority--);
                }
            }
            if (props.wearerCapacityModifiers != null)
            {
                foreach (PawnCapacityModifier capMod in props.wearerCapacityModifiers)
                {
                    if (capMod.capacity == null)
                    {
                        continue;
                    }
                    if (capMod.offset != 0f)
                    {
                        float offset = capMod.offset * multiplier;
                        yield return Entry(category, "MPA_Stat_Wearer".Translate(capMod.capacity.label),
                            (offset > 0f ? "+" : "") + offset.ToStringPercent(), capMod.capacity.description, priority--);
                    }
                    if (capMod.postFactor != 1f)
                    {
                        yield return Entry(category, "MPA_Stat_Wearer".Translate(capMod.capacity.label),
                            "x" + ArmorModuleUtility.ScaleFactor(capMod.postFactor, multiplier).ToStringPercent(), capMod.capacity.description, priority--);
                    }
                }
            }
            if (props.wearerPainFactor != 1f)
            {
                yield return Entry(category, "MPA_Stat_Pain".Translate(),
                    "x" + ArmorModuleUtility.ScaleFactor(props.wearerPainFactor, multiplier).ToStringPercent(), "MPA_Stat_PainDesc".Translate(), priority--);
            }
            if (props.wearerBleedFactor != 1f)
            {
                yield return Entry(category, "MPA_Stat_Bleeding".Translate(),
                    "x" + ArmorModuleUtility.ScaleFactor(props.wearerBleedFactor, multiplier).ToStringPercent(), "MPA_Stat_BleedingDesc".Translate(), priority--);
            }
            if (props.armorStatOffsets != null)
            {
                foreach (StatModifier mod in props.armorStatOffsets)
                {
                    yield return Entry(category, "MPA_Stat_ArmorPiece".Translate(mod.stat.label),
                        mod.stat.ValueToString(mod.value * multiplier, ToStringNumberSense.Offset), mod.stat.description, priority--);
                }
            }
            if (props.armorStatFactors != null)
            {
                foreach (StatModifier mod in props.armorStatFactors)
                {
                    yield return Entry(category, "MPA_Stat_ArmorPiece".Translate(mod.stat.label),
                        "x" + ArmorModuleUtility.ScaleFactor(mod.value, multiplier).ToStringPercent(), mod.stat.description, priority--);
                }
            }
            if (props.computationalLoadBonus != 0f)
            {
                yield return Entry(category, "MPA_Stat_LoadBonus".Translate(),
                    "+" + (props.computationalLoadBonus * multiplier).ToString("0.##"), "MPA_Stat_LoadBonusDesc".Translate(), priority--);
            }
            if (props.bionicSyncPerImplant != 0f)
            {
                yield return Entry(category, "MPA_Stat_BionicSync".Translate(),
                    "MPA_Stat_BionicSyncValue".Translate((props.bionicSyncPerImplant * multiplier).ToStringPercent("0.#")),
                    "MPA_Stat_BionicSyncDesc".Translate(props.bionicSyncMinTechLevel.ToStringHuman()), priority--);
            }
        }

        private static StatDrawEntry Entry(StatCategoryDef category, string label, string value, string description, int priority)
        {
            return new StatDrawEntry(category, label.CapitalizeFirst(), value, description ?? "", priority);
        }
    }
}
