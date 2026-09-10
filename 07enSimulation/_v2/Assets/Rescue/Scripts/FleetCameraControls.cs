using UnityEngine;
namespace RescueSim
{
    // Operates only on cameras; boat keyboard commands retain W/S/A/D.
    [DefaultExecutionOrder(500)]
    public sealed class FleetCameraControls:MonoBehaviour
    {
        public FloodEnvironment environment;
        Vector3 homePosition,pivot,lastMouse;
        Quaternion homeRotation;
        float homeSize;
        int drag=-1;
        bool initialized;
        public void Initialize(FloodEnvironment value)
        {
            if(initialized)return;environment=value;
            var c=environment.overview;homePosition=c.transform.position;homeRotation=c.transform.rotation;homeSize=c.orthographicSize;
            pivot=Ground(c,new Vector2(Screen.width*.5f,Screen.height*.5f));initialized=true;
        }
        Vector3 Ground(Camera c,Vector2 screen)
        {
            Ray ray=c.ScreenPointToRay(screen);var plane=new Plane(Vector3.up,new Vector3(0,environment.water.level,0));
            return plane.Raycast(ray,out float distance)?ray.GetPoint(distance):pivot;
        }
        void Detach()
        {
            if(environment.overview.enabled)return;
            var a=environment.overview;var b=environment.follow;
            a.transform.SetPositionAndRotation(b.transform.position,b.transform.rotation);a.orthographicSize=b.orthographicSize;
            environment.SetFollowCamera(false);pivot=Ground(a,new Vector2(Screen.width*.5f,Screen.height*.5f));
        }
        public void Pan(Vector2 from,Vector2 to)
        {
            Detach();var c=environment.overview;
            float units=2*c.orthographicSize/Mathf.Max(1,c.pixelHeight);
            Vector2 delta=from-to;
            Vector3 shift=(c.transform.right*delta.x+c.transform.up*delta.y)*units;
            c.transform.position+=shift;pivot+=shift;
        }
        public void Orbit(Vector2 pixels)
        {
            Detach();var c=environment.overview;
            float distance=Vector3.Distance(c.transform.position,pivot);
            float pitch=c.transform.eulerAngles.x;if(pitch>180)pitch-=360;
            Quaternion rotation=Quaternion.Euler(Mathf.Clamp(pitch-pixels.y*.25f,-89,89),c.transform.eulerAngles.y+pixels.x*.25f,0);
            c.transform.SetPositionAndRotation(pivot-rotation*Vector3.forward*distance,rotation);
        }
        public void Zoom(float wheel,Vector2 cursor)
        {
            var c=environment.overview.enabled?environment.overview:environment.follow;
            float oldSize=c.orthographicSize;c.orthographicSize=Mathf.Clamp(oldSize*Mathf.Exp(-wheel*.15f),.025f,2);
            if(c==environment.overview)
            {
                Vector2 offset=cursor-new Vector2(c.pixelRect.center.x,c.pixelRect.center.y);
                Vector3 shift=(c.transform.right*offset.x+c.transform.up*offset.y)*2*(oldSize-c.orthographicSize)/Mathf.Max(1,c.pixelHeight);
                c.transform.position+=shift;pivot+=shift;
            }
        }
        public void ResetView()
        {
            environment.SetFollowCamera(false);var c=environment.overview;c.transform.SetPositionAndRotation(homePosition,homeRotation);c.orthographicSize=homeSize;
            pivot=Ground(c,new Vector2(Screen.width*.5f,Screen.height*.5f));drag=-1;
        }
        public void FocusBoat()
        {
            Detach();Vector3 target=environment.boat.transform.position;target.y=environment.water.level;
            environment.overview.transform.position+=target-pivot;pivot=target;environment.overview.orthographicSize=.14f;
        }
        void Update()
        {
            if(!initialized)return;
            if(Input.GetKeyDown(KeyCode.Home))ResetView();
            if(Input.GetKeyDown(KeyCode.F))FocusBoat();
            float scale=Mathf.Max(.6f,Screen.height/900f);Vector3 mouse=Input.mousePosition;
            bool inScene=mouse.x>320*scale&&mouse.x<Screen.width-316*scale&&mouse.y>=0&&mouse.y<=Screen.height;
            if(environment.dashboard)inScene=environment.dashboard.SceneContains(mouse);
            if(inScene)
            {
                if(Input.GetMouseButtonDown(0)){drag=0;lastMouse=mouse;}
                if(Input.GetMouseButtonDown(2)){drag=2;lastMouse=mouse;}
                if(Input.GetMouseButtonDown(1)){drag=1;lastMouse=mouse;}
                if(Input.mouseScrollDelta.y!=0)Zoom(Input.mouseScrollDelta.y,mouse);
            }
            if(drag>=0)
            {
                if(!Input.GetMouseButton(drag)||!inScene)drag=-1;
                else {Vector2 delta=mouse-lastMouse;if(drag==1)Orbit(delta);else Pan(lastMouse,mouse);lastMouse=mouse;}
            }
            Vector2 arrows=new Vector2((Input.GetKey(KeyCode.RightArrow)?1:0)-(Input.GetKey(KeyCode.LeftArrow)?1:0),(Input.GetKey(KeyCode.UpArrow)?1:0)-(Input.GetKey(KeyCode.DownArrow)?1:0));
            if(arrows!=Vector2.zero)
            {
                Detach();var c=environment.overview;Vector3 forward=Vector3.ProjectOnPlane(c.transform.forward,Vector3.up).normalized;
                Vector3 shift=(c.transform.right*arrows.x+forward*arrows.y)*c.orthographicSize*Time.unscaledDeltaTime;
                c.transform.position+=shift;pivot+=shift;
            }
        }
        void OnApplicationFocus(bool focused){if(!focused)drag=-1;}
    }
}
