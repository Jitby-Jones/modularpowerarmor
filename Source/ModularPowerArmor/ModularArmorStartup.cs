using System.Collections.Generic;
using System.Linq;
using RimWorld;
using UnityEngine;
using Verse;

namespace ModularPowerArmor
{
    [StaticConstructorOnStartup]
    public static class ArmorModuleTextures
    {
        public static readonly Texture2D ModifyArmor = ContentFinder<Texture2D>.Get("ModularPowerArmor/UI/ModifyArmor");

        public static readonly Texture2D CooldownBar = SolidColorMaterials.NewSolidColorTexture(new Color32(9, 203, 4, 64));

        public static readonly Texture2D LoadBar = SolidColorMaterials.NewSolidColorTexture(new Color(0.25f, 0.5f, 0.7f));

        public static readonly Texture2D OverloadBar = SolidColorMaterials.NewSolidColorTexture(new Color(0.7f, 0.2f, 0.15f));
    }

    /// <summary>
    /// Runs once all defs are loaded: turns the listed armor into modular armor, gives humanlike
    /// races the comp that draws module visuals, hooks the research into the tree, and gates
    /// module recipes behind it.
    /// </summary>
    [StaticConstructorOnStartup]
    public static class ModularArmorStartup
    {
        private const string MarineArmorDef = "Apparel_PowerArmor";
        private const string MarineArmorResearchFallback = "PoweredArmor";

        static ModularArmorStartup()
        {
            int enabled = 0;
            foreach (ModularArmorTargetDef targetDef in DefDatabase<ModularArmorTargetDef>.AllDefsListForReading)
            {
                foreach (ModularArmorTarget target in targetDef.targets)
                {
                    ThingDef def = DefDatabase<ThingDef>.GetNamedSilentFail(target.defName);
                    if (def == null)
                    {
                        continue; // From a DLC or mod that isn't active.
                    }
                    if (def.apparel == null)
                    {
                        Log.Warning($"[Modular Power Armor] {def.defName} is listed in {targetDef.defName} but isn't apparel; skipping it.");
                        continue;
                    }
                    MakeModular(def, target.slot, target.computationalLoad, target.fit);
                    enabled++;
                }
            }

            foreach (ThingDef def in DefDatabase<ThingDef>.AllDefsListForReading)
            {
                CompProperties_ModularArmor armorProps = def.GetCompProperties<CompProperties_ModularArmor>();
                if (armorProps != null && !def.statBases.StatListContains(MPA_DefOf.MPA_ComputationalLoad))
                {
                    // Declared directly in another mod's XML without a load stat.
                    StatUtility.SetStatValueInList(ref def.statBases, MPA_DefOf.MPA_ComputationalLoad, armorProps.defaultComputationalLoad);
                }
                if (def.race != null && def.race.Humanlike && !def.HasComp(typeof(CompModularArmorRenderer)))
                {
                    if (def.comps == null)
                    {
                        def.comps = new List<CompProperties>();
                    }
                    def.comps.Add(new CompProperties_ModularArmorRenderer());
                }
            }

            ArmorModuleUtility.CacheModuleDefs();
            SetUpResearch();
            AssignModuleResearch();
            SetUpModulusRecipes();

            Log.Message($"[Modular Power Armor] Enabled modular systems on {enabled} armor pieces with {ArmorModuleUtility.AllModuleDefs.Count} modifications available.");
        }

        private static void MakeModular(ThingDef def, ArmorSlot slot, float computationalLoad, string fit)
        {
            if (def.comps == null)
            {
                def.comps = new List<CompProperties>();
            }
            CompProperties_ModularArmor props = def.GetCompProperties<CompProperties_ModularArmor>();
            if (props == null)
            {
                props = new CompProperties_ModularArmor { slot = slot, fit = fit };
                def.comps.Add(props);
                props.ResolveReferences(def);
            }
            else if (props.fit.NullOrEmpty())
            {
                props.fit = fit;
            }
            StatUtility.SetStatValueInList(ref def.statBases, MPA_DefOf.MPA_ComputationalLoad, computationalLoad);
        }

        /// <summary>
        /// Armor Modulus bills take armor as their first ingredient. Which armor is modular is only
        /// known now, so the XML lists marine armor as a placeholder and every modular piece that
        /// fits the bill's modification is allowed here.
        /// </summary>
        private static void SetUpModulusRecipes()
        {
            List<ThingDef> armorDefs = DefDatabase<ThingDef>.AllDefsListForReading
                .Where(def => def.GetCompProperties<CompProperties_ModularArmor>() != null)
                .ToList();
            foreach (RecipeDef recipe in DefDatabase<RecipeDef>.AllDefsListForReading)
            {
                if (recipe.workerClass == null || !typeof(RecipeWorker_ArmorModulus).IsAssignableFrom(recipe.workerClass) || recipe.ingredients.NullOrEmpty())
                {
                    continue;
                }
                ArmorModulusRecipe extension = recipe.GetModExtension<ArmorModulusRecipe>();
                CompProperties_ArmorModule moduleProps = ArmorModuleUtility.PropsOf(extension?.module);
                if (extension == null || (!extension.strip && moduleProps == null))
                {
                    Log.Error($"[Modular Power Armor] Armor Modulus recipe {recipe.defName} needs a ModularPowerArmor.ArmorModulusRecipe extension naming a modification, or strip.");
                    continue;
                }
                ThingFilter armorFilter = recipe.ingredients[0].filter;
                foreach (ThingDef def in armorFilter.AllowedThingDefs.ToList())
                {
                    if (def.GetCompProperties<CompProperties_ModularArmor>() == null)
                    {
                        SetAllow(recipe, def, false);
                    }
                }
                foreach (ThingDef armorDef in armorDefs)
                {
                    ArmorSlot slot = armorDef.GetCompProperties<CompProperties_ModularArmor>().slot;
                    SetAllow(recipe, armorDef, extension.strip || moduleProps.FitsSlot(slot));
                }
                recipe.fixedIngredientFilter?.RecalculateDisplayRootCategory();
                recipe.defaultIngredientFilter?.RecalculateDisplayRootCategory();
            }
        }

        private static void SetAllow(RecipeDef recipe, ThingDef def, bool allow)
        {
            recipe.ingredients[0].filter.SetAllow(def, allow);
            recipe.fixedIngredientFilter?.SetAllow(def, allow);
            recipe.defaultIngredientFilter?.SetAllow(def, allow);
        }

        /// <summary>
        /// Armor modification branches off whichever project unlocks marine armor, and both of the
        /// mod's projects are placed beside it in the research tree.
        /// </summary>
        private static void SetUpResearch()
        {
            ResearchProjectDef armorModification = MPA_DefOf.MPA_Research_ArmorModification;
            ResearchProjectDef marine = MarineArmorResearch();
            if (marine == null)
            {
                Log.Warning("[Modular Power Armor] Couldn't find the research that unlocks marine armor; armor modification has no prerequisite.");
                return;
            }
            if (armorModification.prerequisites == null)
            {
                armorModification.prerequisites = new List<ResearchProjectDef>();
            }
            if (!armorModification.prerequisites.Contains(marine))
            {
                armorModification.prerequisites.Add(marine);
            }
            PlaceBeside(armorModification, marine);
            PlaceBeside(MPA_DefOf.MPA_Research_AdvancedModules, armorModification);
        }

        private static ResearchProjectDef MarineArmorResearch()
        {
            ThingDef marine = DefDatabase<ThingDef>.GetNamedSilentFail(MarineArmorDef);
            ResearchProjectDef research = marine?.recipeMaker?.researchPrerequisite
                ?? marine?.recipeMaker?.researchPrerequisites?.FirstOrDefault();
            if (research == null && marine != null)
            {
                foreach (RecipeDef recipe in DefDatabase<RecipeDef>.AllDefsListForReading)
                {
                    if (recipe.ProducedThingDef == marine)
                    {
                        research = recipe.researchPrerequisite ?? recipe.researchPrerequisites?.FirstOrDefault();
                        if (research != null)
                        {
                            break;
                        }
                    }
                }
            }
            return research ?? DefDatabase<ResearchProjectDef>.GetNamedSilentFail(MarineArmorResearchFallback);
        }

        /// <summary>
        /// Puts a project in the first free spot to the right of <paramref name="anchor"/>, in the
        /// same research tab, so it reads as a branch of it.
        /// </summary>
        private static void PlaceBeside(ResearchProjectDef project, ResearchProjectDef anchor)
        {
            project.tab = anchor.tab;
            List<ResearchProjectDef> others = DefDatabase<ResearchProjectDef>.AllDefsListForReading
                .Where(other => other != project && other.tab == anchor.tab)
                .ToList();
            float[] rowOffsets = { 0f, 0.7f, -0.7f, 1.4f, -1.4f, 2.1f, -2.1f };
            for (int column = 1; column <= 4; column++)
            {
                foreach (float rowOffset in rowOffsets)
                {
                    float x = anchor.researchViewX + column;
                    float y = anchor.researchViewY + rowOffset;
                    if (y < 0f)
                    {
                        continue;
                    }
                    if (others.All(other => Mathf.Abs(other.researchViewX - x) > 0.8f || Mathf.Abs(other.researchViewY - y) > 0.55f))
                    {
                        project.researchViewX = x;
                        project.researchViewY = y;
                        return;
                    }
                }
            }
        }

        /// <summary>Modification recipes from other mods that don't name a research get armor modification.</summary>
        private static void AssignModuleResearch()
        {
            ResearchProjectDef research = MPA_DefOf.MPA_Research_ArmorModification;
            foreach (RecipeDef recipe in DefDatabase<RecipeDef>.AllDefsListForReading)
            {
                ThingDef product = recipe.ProducedThingDef;
                if (product == null || product.GetCompProperties<CompProperties_ArmorModule>() == null)
                {
                    continue;
                }
                if (recipe.researchPrerequisite == null && recipe.researchPrerequisites.NullOrEmpty())
                {
                    recipe.researchPrerequisite = research;
                }
            }
        }
    }
}
