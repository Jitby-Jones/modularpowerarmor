using UnityEngine;
using Verse;

namespace ModularPowerArmor
{
    public class ModularPowerArmorSettings : ModSettings
    {
        public const float DefaultQualityStep = 0.15f;
        public const float DefaultNpcModuleChance = 0.2f;

        /// <summary>How much each quality tier above or below Normal changes a modification's effects.</summary>
        public float qualityStep = DefaultQualityStep;

        /// <summary>Chance that power armor worn by a generated non-player pawn comes with modifications.</summary>
        public float npcModuleChance = DefaultNpcModuleChance;

        public bool renderModuleGraphics = true;

        public override void ExposeData()
        {
            base.ExposeData();
            Scribe_Values.Look(ref qualityStep, "qualityStep", DefaultQualityStep);
            Scribe_Values.Look(ref npcModuleChance, "npcModuleChance", DefaultNpcModuleChance);
            Scribe_Values.Look(ref renderModuleGraphics, "renderModuleGraphics", true);
        }
    }

    public class ModularPowerArmorMod : Mod
    {
        public static ModularPowerArmorSettings Settings;

        public ModularPowerArmorMod(ModContentPack content) : base(content)
        {
            Settings = GetSettings<ModularPowerArmorSettings>();
        }

        public override string SettingsCategory()
        {
            return "MPA_SettingsCategory".Translate();
        }

        public override void DoSettingsWindowContents(Rect inRect)
        {
            Listing_Standard listing = new Listing_Standard();
            listing.Begin(inRect);

            listing.Label("MPA_Setting_QualityStep".Translate(Settings.qualityStep.ToStringPercent()), -1f, "MPA_Setting_QualityStepDesc".Translate());
            Settings.qualityStep = Mathf.Round(listing.Slider(Settings.qualityStep, 0f, 0.5f) * 100f) / 100f;
            listing.Gap();

            listing.Label("MPA_Setting_NpcChance".Translate(Settings.npcModuleChance.ToStringPercent()), -1f, "MPA_Setting_NpcChanceDesc".Translate());
            Settings.npcModuleChance = Mathf.Round(listing.Slider(Settings.npcModuleChance, 0f, 1f) * 100f) / 100f;
            listing.Gap();

            listing.CheckboxLabeled("MPA_Setting_RenderGraphics".Translate(), ref Settings.renderModuleGraphics, "MPA_Setting_RenderGraphicsDesc".Translate());
            listing.Gap();

            if (listing.ButtonText("MPA_Setting_Reset".Translate()))
            {
                Settings.qualityStep = ModularPowerArmorSettings.DefaultQualityStep;
                Settings.npcModuleChance = ModularPowerArmorSettings.DefaultNpcModuleChance;
                Settings.renderModuleGraphics = true;
            }

            listing.End();
        }

        public override void WriteSettings()
        {
            base.WriteSettings();
            ArmorModuleUtility.Notify_SettingsChanged();
        }
    }
}
