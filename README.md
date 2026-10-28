# Modular Power Armor

A RimWorld mod (1.5 and 1.6) that lets you install modifications into power armor the way you install bionics into pawns. Each armor piece has a **Computational Load** budget. Every modification costs some of it, comes in qualities like weapons and armor, and many of them show up on the pawn wearing them.

No Harmony required. Combat Extended is fully supported.

![Preview](About/Preview.png)

## Supported armor

Armor from DLCs or mods you don't have is skipped automatically, with no errors.

| Armor | Body def / helmet def | Source | Computational load (body / helmet) |
|---|---|---|---|
| Marine | `Apparel_PowerArmor` / `Apparel_PowerArmorHelmet` | Core | 10 / 6 |
| Recon | `Apparel_ArmorRecon` / `Apparel_ArmorHelmetRecon` | Core | 12 / 7 |
| Cataphract | `Apparel_ArmorCataphract` / `Apparel_ArmorHelmetCataphract` | Royalty | 9 / 6 |
| Locust | `Apparel_ArmorLocust` (uses the recon helmet) | Royalty | 11 |
| Phoenix | `Apparel_ArmorCataphractPhoenix` (uses the cataphract helmet) | Royalty | 9 |
| Prestige marine | `Apparel_ArmorMarinePrestige` / `Apparel_ArmorMarineHelmetPrestige` | Royalty | 12 / 7 |
| Prestige recon | `Apparel_ArmorReconPrestige` / `Apparel_ArmorHelmetReconPrestige` | Royalty | 14 / 8 |
| Prestige cataphract | `Apparel_ArmorCataphractPrestige` / `Apparel_ArmorHelmetCataphractPrestige` | Royalty | 11 / 7 |
| Prestige locust | `Apparel_ArmorLocustPrestige` | Vanilla Prestige Specialist Armours Reworked / Prestige Specialist Armor | 13 |
| Prestige phoenix | `Apparel_ArmorPhoenixPrestige` | Vanilla Prestige Specialist Armours Reworked / Prestige Specialist Armor | 11 |
| Siegebreaker | `VAE_Apparel_HeavyMarineArmor` / `VAE_Headgear_HeavyMarineHelmet` | Vanilla Armour Expanded | 9 / 6 |
| Prestige siegebreaker | `VAE_Apparel_RoyalSiegeArmor` / `VAE_Headgear_RoyalSiegeHelmet` | Vanilla Armour Expanded + Royalty | 11 / 7 |
| Trooper | `VAE_Apparel_TrooperArmor` / `VAE_Headgear_TrooperHelmet` | Vanilla Armour Expanded | 10 / 6 |
| Prestige trooper | `VAE_Apparel_RoyalTrooperArmor` / `VAE_Headgear_RoyalTrooperHelmet` | Vanilla Armour Expanded + Royalty | 12 / 7 |
| Privateer | `VFEP_Apparel_Privateer` (no separate helmet) | Vanilla Factions Expanded - Pirates | 10 |

Every def name above was checked against Combat Extended's compatibility patches for those mods. The list lives in [`Defs/Targets/MPA_ArmorTargets.xml`](Defs/Targets/MPA_ArmorTargets.xml).

## Computational load

- Each armor piece has its own **Computational Load** stat, shown in its info card. Helmets and body armor have separate onboard computers, so they have separate budgets.
- Each modification has a **computational load cost**. The total cost of a piece's modifications can't exceed its computational load.
- The auxiliary co-processor raises a piece's computational load and costs nothing itself. You can't remove it if the remaining modifications wouldn't fit without it.
- Each modification can only be installed once per piece.

## Modifications

Values are at Normal quality.

| Modification | Fits | Load | Effect | Combat Extended |
|---|---|---|---|---|
| Additional plating | Body + helmet | 2 | Piece: +20% sharp armor, +9% blunt armor | +4 mm RHA sharp, +9 MPa blunt |
| Bionic synchronization | Body + helmet | 3 | Other modifications on the same piece are 2% stronger per bionic-grade (spacer or better) implant in the wearer | Same |
| Thermal regulation unit | Body + helmet | 1 | Wearer: min comfortable temperature -8°C, max +8°C | Same |
| Ablative heat shielding | Body + helmet | 1 | Piece: +15% heat armor, x50% flammability | Same (CE heat armor is still a percentage) |
| Trauma response suite | Body + helmet | 2 | Wearer: x75% bleeding, x85% pain | Same |
| Auxiliary co-processor | Body + helmet | 0 | Piece: +3 computational load | Same |
| Neural stress dampener | Body + helmet | 2 | Wearer: -4% mental break threshold | Also x85% suppressability |
| Targeting uplink | Helmet | 3 | Wearer: x85% aiming time | Also +10% aiming accuracy |
| Multispectral visor | Helmet | 2 | Wearer: x110% sight | Same |
| Biogel servo replacement | Body | 3 | Wearer: x115% manipulation, x105% move speed | Same |
| Load-bearing exoframe | Body | 2 | Wearer: x125% carrying capacity, x110% melee damage | Also +25 kg carry weight, +5 bulk |

Modifications are crafted at a **fabrication bench** and require the **powered armor** research. If that project isn't found, **advanced fabrication** is used instead. Crafting skill decides their quality, as it does for weapons and armor. Non-player pawns' armor has a 20% chance per piece to come with one to three modifications, so you can also loot them.

## Quality

Each quality tier above or below Normal changes a modification's effects by 15% (configurable in the mod settings):

- **Offsets** (armor, temperature, load bonus, ...) are multiplied by the effect strength.
- **Factors** have their distance from 100% multiplied, so a x115% bonus becomes x117.25% at Good quality.

| Quality | Effect strength | Biogel servo: manipulation / move speed | Additional plating: sharp / blunt (vanilla) | Additional plating (CE) | Bionic sync per implant |
|---|---|---|---|---|---|
| Awful | 70% | x110.5% / x103.50% | +14% / +6.3% | +2.8 mm RHA / +6.3 MPa | +1.4% |
| Poor | 85% | x112.8% / x104.25% | +17% / +7.6% | +3.4 mm RHA / +7.6 MPa | +1.7% |
| Normal | 100% | x115.0% / x105.00% | +20% / +9.0% | +4.0 mm RHA / +9.0 MPa | +2.0% |
| Good | 115% | x117.2% / x105.75% | +23% / +10.3% | +4.6 mm RHA / +10.3 MPa | +2.3% |
| Excellent | 130% | x119.5% / x106.50% | +26% / +11.7% | +5.2 mm RHA / +11.7 MPa | +2.6% |
| Masterwork | 145% | x121.7% / x107.25% | +29% / +13.1% | +5.8 mm RHA / +13.0 MPa | +2.9% |
| Legendary | 160% | x124.0% / x108.00% | +32% / +14.4% | +6.4 mm RHA / +14.4 MPa | +3.2% |

Bionic synchronization multiplies on top of quality. For example, a Legendary plating on a piece with a Normal synchronizer and a wearer with 5 bionics applies at 160% x 110% = 176% strength. Synchronization doesn't affect computational load bonuses, because otherwise removing an implant could overload the armor.

## Installing and removing

Installing or removing a modification takes about 10 seconds, scaled by the worker's general labor speed. Any colonist who can manipulate can do it.

- **Armor someone is wearing:** select the colonist and use the **Modify armor** button. It lists every modification on the map that fits, plus what's installed. The colonist fetches the modification and installs it themselves.
- **From a modification:** select a colonist and right-click a modification item to install it into armor they're wearing.
- **Armor on the ground:** select a colonist and right-click the armor.

Removed modifications keep their quality and hit points. Armor that is destroyed or smelted drops its modifications.

Wearer effects are applied through an **armor modifications** health condition, so they show up in the health tab and in every stat breakdown. Armor effects show in the armor's own stat breakdown.

## Visuals

Modifications with a visual are drawn on the pawn through RimWorld's render tree, so they also show in portraits and the colonist bar. These modifications have one:

- **Body:** plating, thermal fins, trauma canister, co-processor pack, biogel tubes, exoframe.
- **Helmet:** brow plate, neural link node, co-processor, stress-dampener circlet, targeting optic and antenna, glowing visor.

Each visual is drawn just above the armor piece it's installed in and below the next apparel layer. You can turn visuals off in the mod settings.

**The included art is generated placeholder art** ([`Source/Textures/generate_textures.py`](Source/Textures/generate_textures.py)). To replace it, drop in PNGs at the same paths under `Textures/ModularPowerArmor/Worn/`:

- They use the vanilla apparel canvas: 128x128 with `_north`, `_south` and `_east` versions; west mirrors east unless you add `_west`.
- Body overlays are centered on the body and helmet overlays on the head.
- Overlays are drawn once for the male body and scaled for the other body types (`bodyTypeAdjustments`). Set `bodyTypeTextures` to `true` on a render node to use per-body-type files (`_Male`, `_Female`, `_Thin`, `_Fat`, `_Hulk`) instead.
- Set `useArmorColor` to `true` and add `_m` mask textures to tint an overlay with the armor's color.

## Combat Extended

The `Mods/CombatExtended` folder only loads when CE is active:

- Armor bonuses switch to CE's units (mm RHA and MPa). They go onto the armor piece's own stat, which CE reads, so CE's partial armor multipliers still apply.
- All modification items get CE bulk.
- Three modifications gain CE-only effects: the stress dampener reduces suppressability, the targeting uplink adds aiming accuracy, and the exoframe adds carry weight and bulk.
- Night vision is deliberately left alone: CE caches apparel night vision per armor type and quality, so a per-item bonus wouldn't apply reliably.

## Adding your own armor or modifications

To support more armor, add a `ModularArmorTargetDef` in your own mod (no C# needed):

```xml
<ModularPowerArmor.ModularArmorTargetDef>
  <defName>MyMod_ModularTargets</defName>
  <label>my armor</label>
  <targets>
    <li><defName>Apparel_ArmorMarineGrenadier</defName><slot>Body</slot><computationalLoad>10</computationalLoad></li>
  </targets>
</ModularPowerArmor.ModularArmorTargetDef>
```

A modification is any `ThingDef` with `CompQuality`, an `MPA_ComputationalLoadCost` stat and a `ModularPowerArmor.CompProperties_ArmorModule` comp; see [`Defs/Modules`](Defs/Modules) for examples. Available fields:

- `slots`
- `wearerStatOffsets`, `wearerStatFactors`, `wearerCapacityModifiers`, `wearerPainFactor`, `wearerBleedFactor`
- `armorStatOffsets`, `armorStatFactors`
- `computationalLoadBonus`
- `bionicSyncPerImplant`, `bionicSyncMinTechLevel`
- `installTicks`
- `bodyRenderNodes`, `helmetRenderNodes`

## Building

```bash
Source/build.sh
```

This needs the .NET SDK. It builds `1.5/Assemblies` and `1.6/Assemblies` against the `Krafs.Rimworld.Ref` packages, so no RimWorld install is required. To regenerate the placeholder textures (and optionally an alignment preview sheet), run:

```bash
python3 Source/Textures/generate_textures.py --preview /tmp/overlay_preview.png
```

## Status

The code compiles against the RimWorld 1.5 and 1.6 reference assemblies. All XML was checked for field names, enum values, cross-references, textures, translation keys and CE patch targets. It hasn't been play-tested in the game yet. In particular, the placeholder overlay positions may need nudging against the real armor textures.
