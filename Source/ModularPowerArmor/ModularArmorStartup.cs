using System.Collections.Generic;
using RimWorld;
using UnityEngine;
using Verse;

namespace ModularPowerArmor
{
    [StaticConstructorOnStartup]
    public static class ArmorModuleTextures
    {
        public static readonly Texture2D ModifyArmor = ContentFinder<Texture2D>.Get("ModularPowerArmor/UI/ModifyArmor");
    }

    /// <summary>
    /// Runs once all defs are loaded: turns the listed armor into modular armor, gives humanlike
    /// races the comp that draws module visuals, and gates module recipes behind research.
    /// </summary>
    [StaticConstructorOnStartup]
    public static class ModularArmorStartup
    {
        // Tried in order; module recipes that don't set their own prerequisite get the first that exists.
        private static readonly string[] ModuleResearchCandidates = { "PoweredArmor", "AdvancedFabrication" };

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
            AssignModuleResearch();

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

        private static void AssignModuleResearch()
        {
            ResearchProjectDef research = null;
            foreach (string candidate in ModuleResearchCandidates)
            {
                research = DefDatabase<ResearchProjectDef>.GetNamedSilentFail(candidate);
                if (research != null)
                {
                    break;
                }
            }
            if (research == null)
            {
                return;
            }
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
