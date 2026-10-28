using System.Collections.Generic;
using Verse;

namespace ModularPowerArmor
{
    /// <summary>Which part of a power armor set a modular piece is.</summary>
    public enum ArmorSlot
    {
        /// <summary>Work it out from the apparel's layers and coverage.</summary>
        Auto,
        Body,
        Helmet
    }

    /// <summary>
    /// One apparel def that should accept modifications. Defs are looked up by name at startup,
    /// so entries for DLCs or mods that aren't loaded are skipped silently.
    /// </summary>
    public class ModularArmorTarget
    {
        public string defName;
        public ArmorSlot slot = ArmorSlot.Auto;
        public float computationalLoad = 8f;

        /// <summary>
        /// Which armor the module art is drawn for (Marine, Recon, Cataphract, ...): fills the {fit}
        /// token in module texture paths. Armor without its own art uses the closest shape, and
        /// anything unknown falls back to Marine.
        /// </summary>
        public string fit;
    }

    /// <summary>
    /// A list of apparel to make modular. Other mods can add their own armor by defining
    /// another ModularArmorTargetDef; no C# or patching is needed.
    /// </summary>
    public class ModularArmorTargetDef : Def
    {
        public List<ModularArmorTarget> targets = new List<ModularArmorTarget>();

        public override IEnumerable<string> ConfigErrors()
        {
            foreach (string error in base.ConfigErrors())
            {
                yield return error;
            }
            foreach (ModularArmorTarget target in targets)
            {
                if (target.defName.NullOrEmpty())
                {
                    yield return "target with no defName";
                }
                else if (target.computationalLoad < 0f)
                {
                    yield return $"{target.defName} has a negative computational load";
                }
            }
        }
    }
}
