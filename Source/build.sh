#!/usr/bin/env bash
# Builds ModularPowerArmor.dll for every supported RimWorld version into <mod>/<version>/Assemblies.
# Needs the .NET SDK (6 or later). Reference assemblies come from the Krafs.Rimworld.Ref NuGet package,
# so a RimWorld install isn't required.
set -euo pipefail
cd "$(dirname "$0")/ModularPowerArmor"
for version in 1.5 1.6; do
  echo "Building for RimWorld $version"
  dotnet build -c Release --nologo -p:RimWorldVersion="$version" -p:BaseIntermediateOutputPath="obj/$version/"
done
