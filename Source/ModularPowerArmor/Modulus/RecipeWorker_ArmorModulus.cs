using System.Collections.Generic;
using System.Linq;
using RimWorld;
using Verse;

namespace ModularPowerArmor
{
    /// <summary>What an Armor Modulus bill does with the armor brought to it.</summary>
    public class ArmorModulusRecipe : DefModExtension
    {
        /// <summary>The modification an install bill puts into the armor.</summary>
        public ThingDef module;

        /// <summary>Take every modification out of the armor instead.</summary>
        public bool strip;
    }

    /// <summary>
    /// Armor Modulus bills. The armor and the modification are brought to the station, nothing is
    /// used up, and the finished piece comes back out as the bill's product, so it is stored like
    /// any other crafted item. Stripped modifications come out as products too.
    /// </summary>
    public class RecipeWorker_ArmorModulus : RecipeWorker
    {
        private ArmorModulusRecipe extension;

        public ArmorModulusRecipe Extension => extension ?? (extension = recipe.GetModExtension<ArmorModulusRecipe>() ?? new ArmorModulusRecipe());

        /// <summary>Armor only counts as an ingredient when this bill can actually do something with it.</summary>
        public bool IsValidIngredient(Thing thing)
        {
            CompModularArmor armor = thing.TryGetComp<CompModularArmor>();
            if (armor == null)
            {
                return !ArmorModuleUtility.IsSpent(thing);
            }
            if (armor.Wearer != null)
            {
                return false;
            }
            if (Extension.strip)
            {
                return armor.Modules.Count > 0;
            }
            return Extension.module != null && armor.CanInstall(Extension.module).Accepted;
        }

        public override void ConsumeIngredient(Thing ingredient, RecipeDef recipe, Map map)
        {
            // Nothing is used up: MakeProducts has already taken the armor and the modification off
            // the table and hands them back as products.
        }

        public List<Thing> MakeProducts(List<Thing> ingredients, Pawn worker)
        {
            List<Thing> products = new List<Thing>();
            Thing armorThing = ingredients?.FirstOrDefault(t => t.TryGetComp<CompModularArmor>() != null);
            if (armorThing == null)
            {
                return products;
            }
            CompModularArmor armor = armorThing.TryGetComp<CompModularArmor>();
            if (armorThing.Spawned)
            {
                armorThing.DeSpawn();
            }
            products.Add(armorThing);

            if (Extension.strip)
            {
                foreach (Thing module in armor.Modules.ToList())
                {
                    if (armor.TryTakeOut(module, out Thing taken) && taken != null)
                    {
                        products.Add(taken);
                    }
                }
                if (worker != null)
                {
                    Messages.Message("MPA_Stripped".Translate(worker.LabelShort, armorThing.LabelShort, worker.Named("PAWN")),
                        worker, MessageTypeDefOf.SilentInput, false);
                }
                return products;
            }

            foreach (Thing ingredient in ingredients)
            {
                if (ingredient == armorThing || ArmorModuleUtility.PropsOf(ingredient) == null)
                {
                    continue;
                }
                if (ingredient.Spawned)
                {
                    ingredient.DeSpawn();
                }
                string moduleLabel = ingredient.LabelNoCount;
                if (armor.TryInstall(ingredient, null))
                {
                    if (worker != null)
                    {
                        Messages.Message("MPA_Installed".Translate(worker.LabelShort, moduleLabel, armorThing.LabelShort, worker.Named("PAWN")),
                            worker, MessageTypeDefOf.SilentInput, false);
                    }
                }
                else
                {
                    // It stopped fitting while the bill was underway: hand it back.
                    products.Add(ingredient);
                }
            }
            return products;
        }
    }
}
