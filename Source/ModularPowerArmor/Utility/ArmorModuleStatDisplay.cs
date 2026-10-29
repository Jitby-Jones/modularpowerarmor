using System.Collections.Generic;
using System.Linq;
using RimWorld;
using UnityEngine;
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

        public static IEnumerable<StatDrawEntry> EntriesFor(CompProperties_ArmorModule props, ThingDef def, QualityCategory quality, Thing thing = null)
        {
            StatCategoryDef category = MPA_DefOf.MPA_ArmorModification;
            bool hasQuality = def == null || ArmorModuleUtility.HasQuality(def);
            float multiplier = hasQuality ? ArmorModuleUtility.QualityMultiplier(quality) : 1f;
            int priority = 5000;

            yield return new StatDrawEntry(category, "MPA_Stat_Fits".Translate(), SlotsLabel(props),
                "MPA_Stat_FitsDesc".Translate(), priority--);

            if (!props.exclusionTags.NullOrEmpty())
            {
                List<string> others = ArmorModuleUtility.AllModuleDefs
                    .Where(other => other != def && props.ExcludedBy(ArmorModuleUtility.PropsOf(other)))
                    .Select(other => other.label)
                    .ToList();
                if (others.Count > 0)
                {
                    yield return new StatDrawEntry(category, "MPA_Stat_Excludes".Translate(), others.ToCommaList().CapitalizeFirst(),
                        "MPA_Stat_ExcludesDesc".Translate(), priority--);
                }
            }

            if (hasQuality)
            {
                yield return new StatDrawEntry(category, "MPA_Stat_QualityEffect".Translate(),
                    "x" + multiplier.ToStringPercent(),
                    "MPA_Stat_QualityEffectDesc".Translate(quality.GetLabel(), ArmorModuleUtility.Settings.qualityStep.ToStringPercent()),
                    priority--);
            }
            else
            {
                yield return new StatDrawEntry(category, "MPA_Stat_QualityEffect".Translate(), "MPA_Stat_NoQuality".Translate(),
                    "MPA_Stat_NoQualityDesc".Translate(), priority--);
            }

            if (thing != null && ArmorModuleUtility.IsSpent(thing))
            {
                yield return new StatDrawEntry(category, "MPA_Stat_Spent".Translate(), "Yes".Translate(),
                    "MPA_InspectSpent".Translate(), priority--);
            }

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
            if (props.wearerStatPenaltyFactors != null)
            {
                foreach (StatModifier mod in props.wearerStatPenaltyFactors)
                {
                    yield return Entry(category, "MPA_Stat_Wearer".Translate(mod.stat.label),
                        "x" + ArmorModuleUtility.ScalePenalty(mod.value, multiplier).ToStringPercent(),
                        mod.stat.description + "\n\n" + "MPA_Stat_PenaltyDesc".Translate(), priority--);
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
            if (props.coveredPainFactor != 1f)
            {
                yield return Entry(category, "MPA_Stat_CoveredPain".Translate(),
                    "x" + ArmorModuleUtility.ScaleFactor(props.coveredPainFactor, multiplier).ToStringPercent(), "MPA_Stat_CoveredPainDesc".Translate(), priority--);
            }
            if (props.coveredHealPerDay > 0f)
            {
                yield return Entry(category, "MPA_Stat_CoveredHealing".Translate(),
                    "MPA_Stat_CoveredHealingValue".Translate((props.coveredHealPerDay * multiplier).ToString("0.#")), "MPA_Stat_CoveredHealingDesc".Translate(), priority--);
            }
            if (props.coveredTendIntervalTicks > 0)
            {
                yield return Entry(category, "MPA_Stat_CoveredTending".Translate(),
                    "MPA_Stat_CoveredTendingValue".Translate(Mathf.Clamp01(props.coveredTendQuality * multiplier).ToStringPercent(), props.coveredTendIntervalTicks.ToStringTicksToPeriod()),
                    "MPA_Stat_CoveredTendingDesc".Translate(), priority--);
            }
            if (props.seeThroughObscurement)
            {
                yield return Entry(category, "MPA_Stat_SeeThrough".Translate(), "Yes".Translate(), "MPA_Stat_SeeThroughDesc".Translate(), priority--);
            }
            if (props.preventStagger)
            {
                yield return Entry(category, "MPA_Stat_NoStagger".Translate(), "Yes".Translate(), "MPA_Stat_NoStaggerDesc".Translate(), priority--);
            }
            if (props.refuseDeath)
            {
                yield return Entry(category, "MPA_Stat_RefuseDeath".Translate(), "MPA_Stat_RefuseDeathValue".Translate(),
                    "MPA_Stat_RefuseDeathDesc".Translate(Hediff_DeathRefused.SustainedConsciousness.ToStringPercent(), Hediff_DeathRefused.DurationTicks.ToStringTicksToPeriod()), priority--);
            }
            if (props.longjump != null)
            {
                yield return Entry(category, "MPA_Stat_LongjumpRange".Translate(), (props.longjump.range * multiplier).ToString("0.#"),
                    "MPA_Stat_LongjumpRangeDesc".Translate(), priority--);
                yield return Entry(category, "MPA_Stat_LongjumpCooldown".Translate(),
                    Mathf.RoundToInt(props.longjump.cooldownTicks / Mathf.Max(0.1f, multiplier)).ToStringTicksToPeriod(),
                    "MPA_Stat_LongjumpCooldownDesc".Translate(), priority--);
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
            if (props.wornComputationalLoadBonus != 0f)
            {
                yield return Entry(category, "MPA_Stat_WornLoadBonus".Translate(),
                    "+" + (props.wornComputationalLoadBonus * multiplier).ToString("0.##"), "MPA_Stat_WornLoadBonusDesc".Translate(), priority--);
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
