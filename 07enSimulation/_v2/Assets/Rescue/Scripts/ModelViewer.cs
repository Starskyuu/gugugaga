using System;
using System.Collections;
using System.IO;
using UnityEngine;

namespace RescueSim
{
    public class ModelViewer : MonoBehaviour
    {
        public GameObject[] models;
        public Camera view;
        readonly string[] labels={"Rescue Boat","Rescue Base","Person - Standing","Person - Seated"};
        readonly string[] names={"RescueBoat","RescueBase","RescuePerson_Standing","RescuePerson_Seated"};
        int selected;
        float yaw=145,pitch=25,distance,radius;
        Vector3 center;
        Vector2 panOffset;
        string status="";
        string Folder => Path.Combine(Path.GetDirectoryName(Application.dataPath),"Model_Previews");
        void Start(){Select(0);if(Array.IndexOf(Environment.GetCommandLineArgs(),"-viewerCheck")>=0)StartCoroutine(Check());}
        void Select(int index)
        {
            selected=index;
            for(int i=0;i<models.Length;i++)models[i].SetActive(i==index);
            var renderers=models[index].GetComponentsInChildren<Renderer>();
            var bounds=renderers[0].bounds;foreach(var r in renderers)bounds.Encapsulate(r.bounds);
            center=bounds.center;radius=Mathf.Max(bounds.extents.magnitude,.001f);ResetView();
        }
        void ResetView(){panOffset=Vector2.zero;yaw=145;pitch=25;distance=radius*3.5f;PositionCamera();}
        void PositionCamera()
        {
            view.transform.rotation=Quaternion.Euler(pitch,yaw,0);
            // Keep the orbit pivot on the model. Pan is a camera-space offset,
            // so rotating after panning cannot make the model orbit an empty point.
            view.transform.position=center-view.transform.forward*distance
                +view.transform.right*panOffset.x+view.transform.up*panOffset.y;
            view.nearClipPlane=Mathf.Max(radius*.001f,.00001f);view.farClipPlane=radius*100;
        }
        void Update()
        {
            if(Input.GetKeyDown(KeyCode.R))ResetView();
            if(Input.GetKeyDown(KeyCode.F11))Screen.fullScreen=!Screen.fullScreen;
            if(Input.GetKeyDown(KeyCode.F12))Capture();
            for(int i=0;i<models.Length;i++)if(Input.GetKeyDown((KeyCode)((int)KeyCode.Alpha1+i)))Select(i);
            bool overUI=Input.mousePosition.y>Screen.height-100 || Input.mousePosition.y<42;
            if(!overUI)
            {
                if(Input.GetMouseButton(0)){yaw+=Input.GetAxis("Mouse X")*4;pitch=Mathf.Clamp(pitch-Input.GetAxis("Mouse Y")*4,-85,85);}
                if(Input.GetMouseButton(1)||Input.GetMouseButton(2))panOffset-=new Vector2(Input.GetAxis("Mouse X"),Input.GetAxis("Mouse Y"))*distance*.018f;
                distance=Mathf.Clamp(distance*Mathf.Exp(-Input.mouseScrollDelta.y*.13f),radius*.25f,radius*20);
            }
            PositionCamera();
        }
        public string Capture(string file=null)
        {
            Directory.CreateDirectory(Folder);string path=Path.Combine(Folder,file??(names[selected]+"_"+DateTime.Now.ToString("yyyyMMdd_HHmmss_fff")+".png"));
            var rt=new RenderTexture(1800,1400,24);var old=RenderTexture.active;var oldTarget=view.targetTexture;
            var texture=new Texture2D(1800,1400,TextureFormat.RGB24,false);
            try{rt.Create();view.targetTexture=rt;view.Render();RenderTexture.active=rt;texture.ReadPixels(new Rect(0,0,1800,1400),0,0);texture.Apply();File.WriteAllBytes(path,texture.EncodeToPNG());status="Saved: "+path;}
            finally{view.targetTexture=oldTarget;RenderTexture.active=old;rt.Release();Destroy(rt);Destroy(texture);}
            return path;
        }
        IEnumerator Check()
        {
            for(int i=0;i<models.Length;i++)
            {
                Select(i);yield return null;
                panOffset=new Vector2(radius*.3f,-radius*.2f);PositionCamera();
                var before=view.WorldToViewportPoint(center);
                yaw+=130;pitch=-35;PositionCamera();
                var after=view.WorldToViewportPoint(center);
                if(Vector3.Distance(before,after)>radius*.001f)
                    throw new InvalidOperationException("Orbit center drift: "+names[i]);
                ResetView();Capture(names[i]+"_Preview.png");
            }
            Select(0);Debug.Log("MODEL_VIEWER_CHECK_PASSED");Application.Quit();
        }
        void OnGUI()
        {
            GUI.skin.button.fontSize=15;GUI.skin.label.fontSize=14;
            GUI.Box(new Rect(8,8,Screen.width-16,86),"");
            for(int i=0;i<models.Length;i++){GUI.backgroundColor=selected==i?new Color(.4f,.9f,.75f):Color.white;if(GUI.Button(new Rect(18+i*178,18,170,32),labels[i]))Select(i);}
            GUI.backgroundColor=Color.white;
            if(GUI.Button(new Rect(738,18,100,32),"Reset [R]"))ResetView();
            if(GUI.Button(new Rect(846,18,150,32),"Save PNG [F12]"))Capture();
            GUI.Label(new Rect(18,58,Screen.width-36,25),"Left drag: orbit   |   Right / middle drag: pan   |   Wheel: zoom   |   1-4: model   |   F11: fullscreen");
            GUI.Box(new Rect(8,Screen.height-36,Screen.width-16,28),status.Length>0?status:"MODEL VIEWER  /  "+labels[selected]);
        }
    }
}
