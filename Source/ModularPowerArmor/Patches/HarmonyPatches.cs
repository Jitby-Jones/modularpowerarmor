using System;
using System.Collections.Generic;
using System.Reflection;
using HarmonyLib;
using RimWorld;
using Verse;

namespace ModularPowerArmor
{
    /// <summary>
    /// Effects that no stat or hediff can express (hediff offsets can't raise a capacity that is at
    /// zero, for one), and the hooks the Armor Modulus bills need.
    /// </summary>
    public static class HarmonyPatches
    {
        public const string Id = "JitbyJones.ModularPowerArmor";

        public static void Apply()
        {
            Harmony harmony = new Harmony(Id);
            // One class at a time, so a game update that breaks one patch doesn't take the others with it.
            foreach (Type type in AccessTools.GetTypesFromAssembly(typeof(HarmonyPatches).Assembly))
            {
                try
                {
                    harmony.CreateClassProcessor(type).Patch();
                }
                catch (Exception e)
                {
                    Log.Error($"[Modular Power Armor] Couldn't apply patch {type.Name}: {e}");
                }
            }
            CombatExtendedCompat.Apply(harmony);
        }
    }

    /// <summary>
    /// Multispectral sensor array: sight never drops below what it gives a sighted wearer, so
    /// missing eyes and blinding effects don't matter. Second heart: a headless pawn it sustains
    /// keeps half their consciousness, and breathes if the neck went with the head.
    /// </summary>
    [HarmonyPatch(typeof(PawnCapacityUtility), nameof(PawnCapacityUtility.CalculateCapacityLevel))]
    public static class Patch_PawnCapacityUtility_CalculateCapacityLevel
    {
        public static void Postfix(HediffSet diffSet, PawnCapacityDef capacity, bool forTradePrice, ref float __result)
        {
            Pawn pawn = diffSet?.pawn;
            if (forTradePrice || pawn == null)
            {
                return;
            }
            if (capacity == PawnCapacityDefOf.Sight)
            {
                Hediff_ArmorModifications hediff = ArmorModuleUtility.WearerHediff(pawn);
                if (hediff != null && hediff.SeesThroughObscurement && __result < hediff.SightFloor)
                {
                    __result = hediff.SightFloor;
                }
            }
            else if (capacity == PawnCapacityDefOf.Consciousness)
            {
                if (__result < Hediff_DeathRefused.SustainedConsciousness && DeathRefusalUtility.IsSustained(pawn)
                    && PawnCapacityUtility.CalculateTagEfficiency(diffSet, BodyPartTagDefOf.ConsciousnessSource) <= 0f)
                {
                    __result = Hediff_DeathRefused.SustainedConsciousness;
                }
            }
            else if (capacity == PawnCapacityDefOf.Breathing)
            {
                if (DeathRefusalUtility.IsSustained(pawn))
                {
                    float sustained = DeathRefusalUtility.SustainedBreathing(diffSet);
                    if (sustained > __result)
                    {
                        __result = sustained;
                    }
                }
            }
        }
    }

    /// <summary>Second heart: refuses a death caused by losing the head.</summary>
    [HarmonyPatch(typeof(Pawn), nameof(Pawn.Kill), new[] { typeof(DamageInfo?), typeof(Hediff) })]
    public static class Patch_Pawn_Kill
    {
        public static bool Prefix(Pawn __instance, DamageInfo? dinfo, Hediff exactCulprit)
        {
            return !DeathRefusalUtility.TryRefuseDeath(__instance, dinfo, exactCulprit);
        }
    }

    /// <summary>Rigidity matrix: hits don't stagger the wearer (bullets in vanilla, melee in Combat Extended).</summary>
    [HarmonyPatch(typeof(StaggerHandler), nameof(StaggerHandler.StaggerFor))]
    public static class Patch_StaggerHandler_StaggerFor
    {
        public static bool Prefix(StaggerHandler __instance, ref bool __result)
        {
            if (ArmorModuleUtility.PreventsStagger(__instance.parent))
            {
                __result = false;
                return false;
            }
            return true;
        }
    }

    /// <summary>Multispectral sensor array: weather, smoke and darkness don't spoil the wearer's aim.</summary>
    [HarmonyPatch(typeof(ShotReport), nameof(ShotReport.HitReportFor))]
    public static class Patch_ShotReport_HitReportFor
    {
        private static readonly FieldInfo FactorFromWeather = AccessTools.Field(typeof(ShotReport), "factorFromWeather");
        private static readonly FieldInfo FactorFromCoveringGas = AccessTools.Field(typeof(ShotReport), "factorFromCoveringGas");
        private static readonly FieldInfo OffsetFromDarkness = AccessTools.Field(typeof(ShotReport), "offsetFromDarkness");

        public static void Postfix(Thing caster, ref ShotReport __result)
        {
            if (!(caster is Pawn pawn) || !ArmorModuleUtility.SeesThroughObscurement(pawn))
            {
                return;
            }
            object report = __result;
            FactorFromWeather?.SetValue(report, 1f);
            FactorFromCoveringGas?.SetValue(report, 1f);
            if (OffsetFromDarkness != null && (float)OffsetFromDarkness.GetValue(report) < 0f)
            {
                OffsetFromDarkness.SetValue(report, 0f);
            }
            __result = (ShotReport)report;
        }
    }

    /// <summary>Multispectral sensor array: no work speed penalty in the dark.</summary>
    [HarmonyPatch(typeof(StatPart_Glow), "ActiveFor")]
    public static class Patch_StatPart_Glow_ActiveFor
    {
        public static void Postfix(Thing t, ref bool __result)
        {
            if (__result && t is Pawn pawn && ArmorModuleUtility.SeesThroughObscurement(pawn))
            {
                __result = false;
            }
        }
    }

    /// <summary>Multispectral sensor array: the dark isn't dark to the wearer.</summary>
    [HarmonyPatch(typeof(ThoughtWorker_Dark), "CurrentStateInternal")]
    public static class Patch_ThoughtWorker_Dark
    {
        public static void Postfix(Pawn p, ref ThoughtState __result)
        {
            if (__result.Active && ArmorModuleUtility.SeesThroughObscurement(p))
            {
                __result = ThoughtState.Inactive;
            }
        }
    }

    /// <summary>Armor Modulus: only armor the bill can work on counts as an ingredient.</summary>
    [HarmonyPatch(typeof(Bill), nameof(Bill.IsFixedOrAllowedIngredient), new[] { typeof(Thing) })]
    public static class Patch_Bill_IsFixedOrAllowedIngredient
    {
        public static void Postfix(Bill __instance, Thing thing, ref bool __result)
        {
            if (__result && __instance.recipe?.Worker is RecipeWorker_ArmorModulus worker)
            {
                __result = worker.IsValidIngredient(thing);
            }
        }
    }

    /// <summary>Armor Modulus: the product is the modified armor itself (and anything taken out of it).</summary>
    [HarmonyPatch(typeof(GenRecipe), nameof(GenRecipe.MakeRecipeProducts))]
    public static class Patch_GenRecipe_MakeRecipeProducts
    {
        public static IEnumerable<Thing> Postfix(IEnumerable<Thing> __result, RecipeDef recipeDef, Pawn worker, List<Thing> ingredients)
        {
            foreach (Thing thing in __result)
            {
                yield return thing;
            }
            if (recipeDef?.Worker is RecipeWorker_ArmorModulus modulus)
            {
                foreach (Thing product in modulus.MakeProducts(ingredients, worker))
                {
                    yield return product;
                }
            }
        }
    }

    /// <summary>
    /// Combat Extended aims through its own shift report; the sensor array clears darkness,
    /// weather and smoke from it. Patched by name, so nothing breaks without CE.
    /// </summary>
    public static class CombatExtendedCompat
    {
        private static FieldInfo lightingShift;
        private static FieldInfo weatherShift;
        private static FieldInfo smokeDensity;
        private static FieldInfo blindFiring;

        public static void Apply(Harmony harmony)
        {
            Type verbType = AccessTools.TypeByName("CombatExtended.Verb_LaunchProjectileCE");
            Type reportType = AccessTools.TypeByName("CombatExtended.ShiftVecReport");
            if (verbType == null || reportType == null)
            {
                return;
            }
            MethodInfo method = AccessTools.Method(verbType, "ShiftVecReportFor", new[] { typeof(LocalTargetInfo), typeof(IntVec3) })
                ?? AccessTools.Method(verbType, "ShiftVecReportFor", new[] { typeof(LocalTargetInfo) });
            if (method == null)
            {
                Log.Warning("[Modular Power Armor] Combat Extended's aiming report wasn't found; the sensor array won't clear darkness and smoke in CE.");
                return;
            }
            lightingShift = AccessTools.Field(reportType, "lightingShift");
            weatherShift = AccessTools.Field(reportType, "weatherShift");
            smokeDensity = AccessTools.Field(reportType, "smokeDensity");
            blindFiring = AccessTools.Field(reportType, "blindFiring");
            try
            {
                harmony.Patch(method, postfix: new HarmonyMethod(typeof(CombatExtendedCompat), nameof(ShiftVecReportPostfix)));
            }
            catch (Exception e)
            {
                Log.Error($"[Modular Power Armor] Couldn't patch Combat Extended's aiming report: {e}");
            }
        }

        public static void ShiftVecReportPostfix(Verb __instance, object __result)
        {
            if (__result == null || !(__instance?.CasterPawn is Pawn pawn) || !ArmorModuleUtility.SeesThroughObscurement(pawn))
            {
                return;
            }
            lightingShift?.SetValue(__result, 0f);
            weatherShift?.SetValue(__result, 0f);
            smokeDensity?.SetValue(__result, 0f);
            blindFiring?.SetValue(__result, false);
        }
    }
}
