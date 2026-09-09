using UnityEditor;
using UnityEngine;
namespace RescueSim.Editor
{
    public sealed class RescueModelImporter : AssetPostprocessor
    {
        void OnPreprocessModel()
        {
            if(!assetPath.StartsWith("Assets/Rescue/Models/"))return;
            var m=(ModelImporter)assetImporter;m.globalScale=1;m.useFileScale=true;m.bakeAxisConversion=true;
            m.importAnimation=false;m.importCameras=false;m.importLights=false;m.isReadable=true;
            m.materialImportMode=ModelImporterMaterialImportMode.ImportStandard;
            m.meshCompression=ModelImporterMeshCompression.Off;m.optimizeMeshPolygons=true;m.optimizeMeshVertices=true;
        }
    }
}
