#!/usr/bin/env bash
# Builds ModularPowerArmor.dll for every supported RimWorld version into <mod>/<version>/Assemblies.
# RimWorld 1.7 targets .NET 10 and needs the .NET 10 SDK; 1.5 and 1.6 target .NET Framework 4.7.2,
# which any .NET 6+ SDK can build. Reference assemblies come from the Krafs.Rimworld.Ref NuGet
# package, so a RimWorld install isn't required.
set -euo pipefail
cd "$(dirname "$0")/ModularPowerArmor"
for version in 1.5 1.6 1.7; do
  echo "Building for RimWorld $version"
  dotnet build -c Release --nologo -p:RimWorldVersion="$version" -p:BaseIntermediateOutputPath="obj/$version/"
done
