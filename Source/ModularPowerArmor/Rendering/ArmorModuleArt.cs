using System.Collections.Generic;
using UnityEngine;
using Verse;

namespace ModularPowerArmor
{
    /// <summary>
    /// Finds the texture a module's render node should use on a given armor piece and body type.
    /// Module art is drawn per armor shape: texture paths contain a {fit} token that becomes the
    /// fit of the armor piece the module is installed in (Marine, Recon, Siegebreaker, ...).
    /// </summary>
    public static class ArmorModuleArt
    {
        public const string FitToken = "{fit}";

        /// <summary>Art used for armor that has no fit of its own, or whose fit has no art for a module.</summary>
        public const string DefaultFit = "Marine";

        private const string DefaultBodyType = "Male";

        private static readonly Dictionary<string, bool> existsCache = new Dictionary<string, bool>();
        private static readonly HashSet<string> warned = new HashSet<string>();

        /// <summary>
        /// The texture path to give Graphic_Multi, or null if there is no art at all.
        /// Tries the armor's fit, then <see cref="DefaultFit"/>; for body textures it also falls
        /// back from a modded body type to Male.
        /// </summary>
        public static string Resolve(string texPath, string fit, string bodyType)
        {
            if (texPath.NullOrEmpty())
            {
                return null;
            }
            foreach (string candidateFit in Fits(texPath, fit))
            {
                string path = texPath.Replace(FitToken, candidateFit);
                if (bodyType != null)
                {
                    if (Exists(path + "_" + bodyType))
                    {
                        return path + "_" + bodyType;
                    }
                    if (bodyType != DefaultBodyType && Exists(path + "_" + DefaultBodyType))
                    {
                        return path + "_" + DefaultBodyType;
                    }
                }
                else if (Exists(path))
                {
                    return path;
                }
            }
            if (warned.Add(texPath + "|" + fit))
            {
                Log.Warning($"[Modular Power Armor] No module art found at {texPath} (fit {fit ?? "none"}, body {bodyType ?? "none"}).");
            }
            return null;
        }

        private static IEnumerable<string> Fits(string texPath, string fit)
        {
            if (!texPath.Contains(FitToken))
            {
                yield return null;
                yield break;
            }
            if (!fit.NullOrEmpty() && fit != DefaultFit)
            {
                yield return fit;
            }
            yield return DefaultFit;
        }

        /// <summary>Whether Graphic_Multi would find any facing at this path.</summary>
        private static bool Exists(string path)
        {
            if (!existsCache.TryGetValue(path, out bool exists))
            {
                exists = ContentFinder<Texture2D>.Get(path + "_south", false) != null
                    || ContentFinder<Texture2D>.Get(path + "_east", false) != null
                    || ContentFinder<Texture2D>.Get(path + "_north", false) != null;
                existsCache[path] = exists;
            }
            return exists;
        }
    }
}
