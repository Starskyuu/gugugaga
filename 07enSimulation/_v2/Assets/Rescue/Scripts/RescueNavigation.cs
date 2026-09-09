using System.Collections.Generic;
using UnityEngine;
namespace RescueSim
{
    // Inflated 2-D occupancy grid over the actual collider/water scene.
    // The path is a reference only; it never writes a boat transform.
    public sealed class RescueNavigation:MonoBehaviour
    {
        public WaterField water;
        public BoatDynamics[] boats;
        public FloatingDebris[] debris;
        public float cell=.025f,clearance=.048f;
        bool[] staticBlocked;
        int nx,nz;
        Vector3 origin;
        float lastLevel=float.NaN;
        public void Rebuild()
        {
            nx=Mathf.RoundToInt(water.boundsSize.x/cell)+1;nz=Mathf.RoundToInt(water.boundsSize.z/cell)+1;
            origin=water.boundsCenter-new Vector3(water.boundsSize.x/2,0,water.boundsSize.z/2);
            staticBlocked=new bool[nx*nz];lastLevel=water.level;
            for(int z=0;z<nz;z++)for(int x=0;x<nx;x++)
            {
                Vector3 p=Point(x+z*nx);bool blocked=x<2||z<2||x>=nx-2||z>=nz-2;
                if(!blocked)
                    foreach(var c in Physics.OverlapBox(p+Vector3.up*.025f,new Vector3(clearance,.055f,clearance),Quaternion.identity,~0,QueryTriggerInteraction.Ignore))
                    {
                        if(c.attachedRigidbody||c.name=="Physical_Seabed"||c.name=="Shallow_Shelf_Collider")continue;
                        blocked=true;break;
                    }
                staticBlocked[x+z*nx]=blocked;
            }
        }
        Vector3 Point(int i)=>origin+new Vector3((i%nx)*cell,water.level,(i/nx)*cell);
        int Index(Vector3 p)=>Mathf.Clamp(Mathf.RoundToInt((p.x-origin.x)/cell),0,nx-1)+nx*Mathf.Clamp(Mathf.RoundToInt((p.z-origin.z)/cell),0,nz-1);
        public bool Walkable(Vector3 p,int boatIndex,bool dynamic=true)
        {
            if(staticBlocked==null||Mathf.Abs(lastLevel-water.level)>.0001f)Rebuild();
            int i=Index(p);if(staticBlocked[i]||!water.HasWater(p))return false;
            // Check the footprint, not just its center, at shallow boundaries.
            float depth=boats[boatIndex].Draft+.0018f;
            foreach(var off in new[]{Vector3.zero,Vector3.right*clearance,Vector3.left*clearance,Vector3.forward*clearance,Vector3.back*clearance})
                if(water.DepthAt(p+off)<Mathf.Max(.008f,depth))return false;
            if(!dynamic)return true;
            for(int b=0;b<boats.Length;b++)if(b!=boatIndex&&boats[b].isActiveAndEnabled&&FlatDistance(p,boats[b].Body.position)<.096f)return false;
            foreach(var d in debris)if(d.isActiveAndEnabled&&FlatDistance(p,d.transform.position)<clearance+Mathf.Max(d.size.x,d.size.z)*.5f)return false;
            return true;
        }
        public static float FlatDistance(Vector3 a,Vector3 b){a.y=b.y=0;return Vector3.Distance(a,b);}
        public bool ClearLine(Vector3 a,Vector3 b,int boatIndex,bool dynamic=true)
        {
            int steps=Mathf.Max(1,Mathf.CeilToInt(FlatDistance(a,b)/(cell*.45f)));
            for(int s=1;s<=steps;s++)if(!Walkable(Vector3.Lerp(a,b,(float)s/steps),boatIndex,dynamic))return false;
            return true;
        }
        int Nearest(Vector3 p,int boatIndex)
        {
            int baseIndex=Index(p),best=-1;float distance=float.PositiveInfinity;
            for(int dz=-4;dz<=4;dz++)for(int dx=-4;dx<=4;dx++)
            {
                int x=baseIndex%nx+dx,z=baseIndex/nx+dz;if(x<0||z<0||x>=nx||z>=nz)continue;
                int i=x+z*nx;float d=(Point(i)-p).sqrMagnitude;
                if(d<distance&&Walkable(Point(i),boatIndex)){distance=d;best=i;}
            }
            return best;
        }
        public List<Vector3> Plan(Vector3 from,Vector3 to,int boatIndex)
        {
            if(staticBlocked==null||Mathf.Abs(lastLevel-water.level)>.0001f)Rebuild();
            int start=Nearest(from,boatIndex),end=Nearest(to,boatIndex);if(start<0||end<0)return null;
            if(FlatDistance(Point(end),to)>.075f)return null;
            int total=nx*nz;var g=new float[total];var parent=new int[total];var closed=new bool[total];
            for(int i=0;i<total;i++){g[i]=float.PositiveInfinity;parent[i]=-1;}
            var open=new List<int>{start};g[start]=0;
            while(open.Count>0)
            {
                int best=0;float score=float.PositiveInfinity;
                for(int k=0;k<open.Count;k++){float f=g[open[k]]+FlatDistance(Point(open[k]),Point(end));if(f<score){score=f;best=k;}}
                int current=open[best];open.RemoveAt(best);if(closed[current])continue;
                if(current==end)
                {
                    var path=new List<Vector3>();for(int n=end;n!=-1;n=parent[n])path.Add(Point(n));path.Reverse();
                    if(Walkable(to,boatIndex)&&ClearLine(path[path.Count-1],to,boatIndex))path.Add(new Vector3(to.x,water.level,to.z));
                    var smooth=new List<Vector3>();Vector3 anchor=from;int cursor=0;
                    while(cursor<path.Count)
                    {
                        int far=cursor;while(far+1<path.Count&&ClearLine(anchor,path[far+1],boatIndex))far++;
                        smooth.Add(path[far]);anchor=path[far];cursor=far+1;
                    }
                    return smooth;
                }
                closed[current]=true;
                for(int dz=-1;dz<=1;dz++)for(int dx=-1;dx<=1;dx++)
                {
                    if(dx==0&&dz==0)continue;int x=current%nx+dx,z=current/nx+dz;if(x<0||z<0||x>=nx||z>=nz)continue;
                    int next=x+z*nx;if(closed[next]||!Walkable(Point(next),boatIndex))continue;
                    if(dx!=0&&dz!=0&&(!Walkable(Point(x+(current/nx)*nx),boatIndex)||!Walkable(Point(current%nx+z*nx),boatIndex)))continue;
                    Vector3 step=Point(next)-Point(current);Vector3 flow=water.VelocityAt(Point(next));
                    float cost=step.magnitude*(1+Mathf.Max(0,-Vector3.Dot(flow,step.normalized))/.04f);
                    float value=g[current]+cost;if(value>=g[next])continue;g[next]=value;parent[next]=current;open.Add(next);
                }
            }
            return null;
        }
    }
}
