using System.Collections.Generic;
using System.Linq;
using System.Text;
using RimWorld;
using Verse;

namespace ModularPowerArmor
{
    /// <summary>
    /// Lives on a modular power armor piece. Holds the installed modifications as real items,
    /// so their quality and hit points survive being installed and removed again.
    /// </summary>
    public class CompModularArmor : ThingComp, IThingHolder
    {
        private ThingOwner<Thing> modules;
        private bool npcModulesRolled;

        [Unsaved] private int syncBonusTick = -1;
        [Unsaved] private float syncBonusCached;

        // Worn armor that is destroyed by damage gets no map in PostDestroy, so remember who was wearing it.
        [Unsaved] private Pawn lastDamagedWearer;
        [Unsaved] private int lastDamagedTick = -1;

        public CompModularArmor()
        {
            modules = new ThingOwner<Thing>(this);
        }

        public CompProperties_ModularArmor Props => (CompProperties_ModularArmor)props;

        public ArmorSlot Slot => Props.slot;

        /// <summary>Which armor's module art to draw on this piece (fills {fit} in module texture paths).</summary>
        public string Fit => Props.fit.NullOrEmpty() ? ArmorModuleArt.DefaultFit : Props.fit;

        public Apparel Apparel => parent as Apparel;

        public Pawn Wearer => Apparel?.Wearer;

        public List<Thing> Modules => modules.InnerListForReading;

        /// <summary>Total computational load this piece supports, including co-processor bonuses.</summary>
        public float Capacity => parent.GetStatValue(MPA_DefOf.MPA_ComputationalLoad);

        public float UsedLoad
        {
            get
            {
                float used = 0f;
                List<Thing> list = Modules;
                for (int i = 0; i < list.Count; i++)
                {
                    used += ArmorModuleUtility.LoadCost(list[i]);
                }
                return used;
            }
        }

        /// <summary>
        /// Bonus to every modification on this piece from bionic synchronization:
        /// sum over synchronization modules of (per-implant bonus x quality) x qualifying implants.
        /// </summary>
        public float SyncBonus
        {
            get
            {
                int tick = CurrentTick;
                if (tick != syncBonusTick)
                {
                    syncBonusCached = ComputeSyncBonus();
                    syncBonusTick = tick;
                }
                return syncBonusCached;
            }
        }

        /// <summary>How strongly a modification installed here applies its effects.</summary>
        public float EffectMultiplier(Thing module)
        {
            return ArmorModuleUtility.QualityMultiplier(module) * (1f + SyncBonus);
        }

        public bool HasModuleOfDef(ThingDef def)
        {
            List<Thing> list = Modules;
            for (int i = 0; i < list.Count; i++)
            {
                if (list[i].def == def)
                {
                    return true;
                }
            }
            return false;
        }

        public AcceptanceReport CanInstall(Thing module)
        {
            CompProperties_ArmorModule moduleProps = ArmorModuleUtility.PropsOf(module);
            if (moduleProps == null)
            {
                return false;
            }
            if (!moduleProps.FitsSlot(Slot))
            {
                return "MPA_Reason_WrongSlot".Translate(ArmorModuleStatDisplay.SlotLabel(Slot)).Resolve();
            }
            if (HasModuleOfDef(module.def))
            {
                return "MPA_Reason_AlreadyInstalled".Translate(module.def.label).Resolve();
            }
            float cost = ArmorModuleUtility.LoadCost(module);
            float available = Capacity - UsedLoad + ArmorModuleUtility.CapacityBonus(module);
            if (cost > available + 0.001f)
            {
                return "MPA_Reason_NotEnoughLoad".Translate(cost.ToString("0.#"), (Capacity - UsedLoad).ToString("0.#")).Resolve();
            }
            return true;
        }

        public AcceptanceReport CanRemove(Thing module)
        {
            if (!modules.Contains(module))
            {
                return false;
            }
            float bonus = ArmorModuleUtility.CapacityBonus(module);
            if (bonus > 0f && UsedLoad - ArmorModuleUtility.LoadCost(module) > Capacity - bonus + 0.001f)
            {
                return "MPA_Reason_RemoveWouldOverload".Translate(module.LabelNoCount).Resolve();
            }
            return true;
        }

        /// <summary>Moves a module into this piece, from a container such as a pawn's carry tracker.</summary>
        public bool TryInstall(Thing module, ThingOwner from)
        {
            if (!CanInstall(module).Accepted)
            {
                return false;
            }
            bool installed = from != null
                ? from.TryTransferToContainer(module, modules, false)
                : modules.TryAdd(module, false);
            if (installed)
            {
                Notify_ModulesChanged();
            }
            return installed;
        }

        /// <summary>Drops a module on the map next to <paramref name="dropCell"/>.</summary>
        public Thing TryRemove(Thing module, IntVec3 dropCell, Map map)
        {
            if (map == null || !modules.Contains(module))
            {
                return null;
            }
            modules.TryDrop(module, dropCell, map, ThingPlaceMode.Near, out Thing dropped);
            if (dropped != null)
            {
                Notify_ModulesChanged();
            }
            return dropped;
        }

        public void Notify_ModulesChanged()
        {
            syncBonusTick = -1;
            Pawn wearer = Wearer;
            if (wearer != null)
            {
                ArmorModuleUtility.Notify_WornModulesChanged(wearer);
            }
        }

        private float ComputeSyncBonus()
        {
            Pawn wearer = Wearer;
            if (wearer == null)
            {
                return 0f;
            }
            float bonus = 0f;
            List<Thing> list = Modules;
            for (int i = 0; i < list.Count; i++)
            {
                CompProperties_ArmorModule moduleProps = ArmorModuleUtility.PropsOf(list[i]);
                if (moduleProps == null || moduleProps.bionicSyncPerImplant <= 0f)
                {
                    continue;
                }
                int implants = ArmorModuleUtility.CountBionicImplants(wearer, moduleProps.bionicSyncMinTechLevel);
                bonus += moduleProps.bionicSyncPerImplant * ArmorModuleUtility.QualityMultiplier(list[i]) * implants;
            }
            return bonus;
        }

        // ---- Stats of the armor piece itself ----

        public override float GetStatOffset(StatDef stat)
        {
            float offset = base.GetStatOffset(stat);
            List<Thing> list = Modules;
            for (int i = 0; i < list.Count; i++)
            {
                offset += ModuleStatOffset(list[i], stat);
            }
            return offset;
        }

        private static int CurrentTick => Current.Game != null ? Find.TickManager.TicksGame : 0;

        public override float GetStatFactor(StatDef stat)
        {
            float factor = base.GetStatFactor(stat);
            List<Thing> list = Modules;
            for (int i = 0; i < list.Count; i++)
            {
                factor *= ModuleStatFactor(list[i], stat);
            }
            return factor;
        }

#if RW_1_5
        public override void GetStatsExplanation(StatDef stat, StringBuilder sb)
        {
            base.GetStatsExplanation(stat, sb);
            AppendStatsExplanation(stat, sb, "");
        }
#else
        public override void GetStatsExplanation(StatDef stat, StringBuilder sb, string whitespace = "")
        {
            base.GetStatsExplanation(stat, sb, whitespace);
            AppendStatsExplanation(stat, sb, whitespace);
        }
#endif

        private void AppendStatsExplanation(StatDef stat, StringBuilder sb, string whitespace)
        {
            List<Thing> list = Modules;
            for (int i = 0; i < list.Count; i++)
            {
                float offset = ModuleStatOffset(list[i], stat);
                if (offset != 0f)
                {
                    sb.AppendLine($"{whitespace}{list[i].LabelCapNoCount}: {stat.ValueToString(offset, ToStringNumberSense.Offset)}");
                }
                float factor = ModuleStatFactor(list[i], stat);
                if (factor != 1f)
                {
                    sb.AppendLine($"{whitespace}{list[i].LabelCapNoCount}: x{factor.ToStringPercent()}");
                }
            }
        }

        private float ModuleStatOffset(Thing module, StatDef stat)
        {
            CompProperties_ArmorModule moduleProps = ArmorModuleUtility.PropsOf(module);
            if (moduleProps == null)
            {
                return 0f;
            }
            if (stat == StatDefOf.MarketValue)
            {
                // Traders pay for installed modifications instead of getting them for free.
                return module.MarketValue;
            }
            if (stat == MPA_DefOf.MPA_ComputationalLoad)
            {
                // Quality only: letting synchronization raise capacity would let removing an implant overload the armor.
                return ArmorModuleUtility.CapacityBonus(module);
            }
            if (moduleProps.armorStatOffsets.NullOrEmpty())
            {
                return 0f;
            }
            float value = moduleProps.armorStatOffsets.GetStatOffsetFromList(stat);
            return value == 0f ? 0f : value * EffectMultiplier(module);
        }

        private float ModuleStatFactor(Thing module, StatDef stat)
        {
            CompProperties_ArmorModule moduleProps = ArmorModuleUtility.PropsOf(module);
            if (moduleProps == null || moduleProps.armorStatFactors.NullOrEmpty())
            {
                return 1f;
            }
            float value = moduleProps.armorStatFactors.GetStatFactorFromList(stat);
            return value == 1f ? 1f : ArmorModuleUtility.ScaleFactor(value, EffectMultiplier(module));
        }

        // ---- UI ----

        public override IEnumerable<Gizmo> CompGetWornGizmosExtra()
        {
            foreach (Gizmo gizmo in base.CompGetWornGizmosExtra())
            {
                yield return gizmo;
            }
            Pawn wearer = Wearer;
            // One button per pawn, even when wearing both a modular helmet and modular armor.
            if (wearer == null || !wearer.IsColonistPlayerControlled || ArmorModuleUtility.FirstWornModularArmor(wearer) != this)
            {
                yield break;
            }
            yield return new Command_Action
            {
                defaultLabel = "MPA_ModifyArmor".Translate(),
                defaultDesc = "MPA_ModifyArmorDesc".Translate(),
                icon = ArmorModuleTextures.ModifyArmor,
                // Each pawn gets its own menu; grouping would open one menu per selected pawn at once.
                groupable = false,
                action = () => Find.WindowStack.Add(new FloatMenu(ArmorModuleMenus.WornArmorOptions(wearer)))
            };
        }

        public override IEnumerable<FloatMenuOption> CompFloatMenuOptions(Pawn selPawn)
        {
            foreach (FloatMenuOption option in base.CompFloatMenuOptions(selPawn))
            {
                yield return option;
            }
            if (!parent.Spawned || Wearer != null)
            {
                yield break;
            }
            foreach (FloatMenuOption option in ArmorModuleMenus.GroundArmorOptions(selPawn, this))
            {
                yield return option;
            }
        }

        public override string CompInspectStringExtra()
        {
            StringBuilder sb = new StringBuilder();
            sb.Append("MPA_InspectLoad".Translate(UsedLoad.ToString("0.#"), Capacity.ToString("0.#")));
            if (modules.Count > 0)
            {
                sb.AppendLine();
                sb.Append("MPA_InspectModules".Translate(Modules.Select(m => m.LabelNoCount).ToCommaList()));
            }
            return sb.ToString();
        }

        public override IEnumerable<StatDrawEntry> SpecialDisplayStats()
        {
            foreach (StatDrawEntry entry in base.SpecialDisplayStats())
            {
                yield return entry;
            }
            yield return new StatDrawEntry(
                StatCategoryDefOf.Apparel,
                "MPA_Stat_LoadInUse".Translate(),
                $"{UsedLoad:0.#} / {Capacity:0.#}",
                "MPA_Stat_LoadInUseDesc".Translate(),
                3001);

            StringBuilder report = new StringBuilder("MPA_Stat_InstalledDesc".Translate());
            if (modules.Count > 0)
            {
                report.AppendLine();
                foreach (Thing module in Modules)
                {
                    report.AppendLine();
                    report.Append($"  - {module.LabelCapNoCount}: {"MPA_Stat_EffectStrength".Translate(EffectMultiplier(module).ToStringPercent())}");
                }
            }
            yield return new StatDrawEntry(
                StatCategoryDefOf.Apparel,
                "MPA_Stat_Installed".Translate(),
                modules.Count.ToString(),
                report.ToString(),
                3000);
        }

        // ---- Lifecycle ----

        public override void Notify_Equipped(Pawn pawn)
        {
            base.Notify_Equipped(pawn);
            if (!npcModulesRolled)
            {
                npcModulesRolled = true;
                ArmorModuleUtility.TryGiveNpcModules(this, pawn);
            }
            syncBonusTick = -1;
            ArmorModuleUtility.Notify_WornModulesChanged(pawn);
        }

        public override void Notify_Unequipped(Pawn pawn)
        {
            base.Notify_Unequipped(pawn);
            syncBonusTick = -1;
            ArmorModuleUtility.Notify_WornModulesChanged(pawn);
        }

        public override void PostPreApplyDamage(ref DamageInfo dinfo, out bool absorbed)
        {
            base.PostPreApplyDamage(ref dinfo, out absorbed);
            Pawn wearer = Wearer;
            if (wearer != null)
            {
                lastDamagedWearer = wearer;
                lastDamagedTick = CurrentTick;
            }
        }

        public override void PostDestroy(DestroyMode mode, Map previousMap)
        {
            base.PostDestroy(mode, previousMap);
            if (modules.Count == 0)
            {
                return;
            }
            // Salvage the modifications when the armor is destroyed or smelted: next to where it was,
            // or at the feet of whoever was wearing it when it was shot to pieces.
            Map map = previousMap;
            IntVec3 cell = parent.Position;
            if (map == null && lastDamagedWearer != null && lastDamagedTick == CurrentTick && lastDamagedWearer.MapHeld != null)
            {
                map = lastDamagedWearer.MapHeld;
                cell = lastDamagedWearer.PositionHeld;
            }
            if (map != null && cell.IsValid && cell.InBounds(map))
            {
                modules.TryDropAll(cell, map, ThingPlaceMode.Near);
            }
            else
            {
                modules.ClearAndDestroyContents();
            }
            lastDamagedWearer = null;
        }

        public override void PostExposeData()
        {
            base.PostExposeData();
            Scribe_Deep.Look(ref modules, "mpaModules", this);
            Scribe_Values.Look(ref npcModulesRolled, "mpaNpcModulesRolled", false);
            if (Scribe.mode == LoadSaveMode.PostLoadInit && modules == null)
            {
                // Armor saved before this mod was added.
                modules = new ThingOwner<Thing>(this);
            }
        }

        // ---- IThingHolder ----

        public ThingOwner GetDirectlyHeldThings()
        {
            return modules;
        }

        public void GetChildHolders(List<IThingHolder> outChildren)
        {
            ThingOwnerUtility.AppendThingHoldersFromThings(outChildren, GetDirectlyHeldThings());
        }
    }
}
