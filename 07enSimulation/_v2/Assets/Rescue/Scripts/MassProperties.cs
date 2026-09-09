using System;
using System.Collections.Generic;
using UnityEngine;

namespace RescueSim
{
    public static class MassProperties
    {
        // Sum box inertias about the combined COM, then diagonalize the complete
        // symmetric tensor. PhysX receives principal moments AND their rotation.
        public static void Calculate(IList<MassPart> parts, out float mass, out Vector3 com,
                                     out Vector3 moments, out Quaternion principalRotation)
        {
            mass = 0; com = Vector3.zero;
            foreach (var p in parts) { mass += p.mass; com += p.position * p.mass; }
            if (mass <= 0) throw new ArgumentException("Positive mass required");
            com /= mass;
            var a = new double[3,3]; var vectors = new double[3,3];
            for (int i=0;i<3;i++) vectors[i,i] = 1;
            foreach (var p in parts)
            {
                Vector3 r = p.position - com, d = p.size;
                a[0,0] += p.mass * (d.y*d.y+d.z*d.z)/12;
                a[1,1] += p.mass * (d.x*d.x+d.z*d.z)/12;
                a[2,2] += p.mass * (d.x*d.x+d.y*d.y)/12;
                for (int i=0;i<3;i++) for (int j=0;j<3;j++)
                    a[i,j] += p.mass * ((i==j ? r.sqrMagnitude : 0) - r[i]*r[j]);
            }
            for (int iteration=0;iteration<24;iteration++)
            {
                int p=0,q=1;
                if (Math.Abs(a[0,2])>Math.Abs(a[p,q])) {p=0;q=2;}
                if (Math.Abs(a[1,2])>Math.Abs(a[p,q])) {p=1;q=2;}
                if (Math.Abs(a[p,q])<1e-16) break;
                double phi=.5*Math.Atan2(2*a[p,q],a[q,q]-a[p,p]);
                double c=Math.Cos(phi), sn=Math.Sin(phi);
                var old=(double[,])a.Clone();
                for(int k=0;k<3;k++){ a[k,p]=c*old[k,p]-sn*old[k,q]; a[k,q]=sn*old[k,p]+c*old[k,q]; }
                old=(double[,])a.Clone();
                for(int k=0;k<3;k++){ a[p,k]=c*old[p,k]-sn*old[q,k]; a[q,k]=sn*old[p,k]+c*old[q,k]; }
                for(int k=0;k<3;k++){ double x=vectors[k,p],y=vectors[k,q]; vectors[k,p]=c*x-sn*y; vectors[k,q]=sn*x+c*y; }
            }
            moments = new Vector3((float)a[0,0],(float)a[1,1],(float)a[2,2]);
            Vector3 up = new Vector3((float)vectors[0,1],(float)vectors[1,1],(float)vectors[2,1]);
            Vector3 forward = new Vector3((float)vectors[0,2],(float)vectors[1,2],(float)vectors[2,2]);
            principalRotation = Quaternion.LookRotation(forward,up);
        }
    }
}
