# Belt Runner ambience renderer: synthesises sfx\space_ambience.wav here, no API involved. A seamless loop of soft
# filtered wind, a faint beating sub drone, a few slowly swelling detuned partials through a long delay and the odd distant
# twinkle. Mono 16-bit, 22050 Hz keeps the file small enough for the base64 pack. The game plays it very quietly under
# everything (MUSIC bed). Run:  powershell -ExecutionPolicy Bypass -File .\gen-ambience.ps1   then build-sfx-data.ps1
param([double]$Seconds=32, [int]$Rate=22050, [int]$Seed=11, [double]$Peak=0.6)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$out=Join-Path $root 'sfx\space_ambience.wav'
Add-Type -TypeDefinition @"
using System;
public static class Ambience {
  public static string Stats="";
  // Renders seconds+fade of sound, then folds the extra tail back over the head with an equal-power crossfade so the
  // loop point is inaudible. Returns 16-bit little-endian PCM, normalised to the requested peak.
  public static byte[] Render(int rate, double seconds, double fade, int seed, double peak){
    Random r=new Random(seed);
    int L=(int)(rate*seconds), F=(int)(rate*fade), n=L+F;
    double dt=1.0/rate, TAU=Math.PI*2;
    double[] a=new double[n];
    // wind: white noise through two one-pole lowpasses whose cutoff wanders slowly
    double lp=0, lp2=0;
    // shimmer: six detuned sine pairs on a minor chord, each swelling on its own slow cycle
    double[] freqs={220.0, 261.63, 329.63, 392.0, 493.88, 587.33};
    int P=freqs.Length;
    double[] ph1=new double[P], ph2=new double[P], per=new double[P], eph=new double[P];
    for(int p=0;p<P;p++){ ph1[p]=r.NextDouble()*TAU; ph2[p]=r.NextDouble()*TAU; per[p]=9+r.NextDouble()*16; eph[p]=r.NextDouble()*TAU; }
    // a long dark delay the shimmer and twinkles echo through
    int dl=(int)(rate*0.41); double[] dbuf=new double[dl]; int di=0; double dlp=0;
    // twinkles: soft high blips every few seconds
    double nextTw=2+r.NextDouble()*4, twT=-1, twF=0;
    double s1=0, s2=0, s3=0, hp=0, hpx=0;
    double eWind=0, eSub=0, eSh=0, eTw=0;
    for(int i=0;i<n;i++){
      double t=i*dt;
      double cut=380+220*Math.Sin(TAU*t/13.0)+120*Math.Sin(TAU*t/29.0+1.0);
      double k=1-Math.Exp(-TAU*cut*dt);
      double w=r.NextDouble()*2-1;
      lp+=k*(w-lp); lp2+=k*(lp-lp2);
      double wind=lp2*(0.55+0.25*Math.Sin(TAU*t/23.0+2.0))*3.5;
      s1+=TAU*55.0*dt; s2+=TAU*55.35*dt; s3+=TAU*110.0*dt;
      double sub=(Math.Sin(s1)*0.6+Math.Sin(s2)*0.4+Math.Sin(s3)*0.15)*(0.10+0.04*Math.Sin(TAU*t/19.0));
      double sh=0;
      for(int p=0;p<P;p++){
        double e=0.5-0.5*Math.Cos(TAU*t/per[p]+eph[p]); e=e*e*e;   // long quiet gaps, brief swells
        ph1[p]+=TAU*freqs[p]*dt; ph2[p]+=TAU*(freqs[p]+0.35)*dt;
        sh+=(Math.Sin(ph1[p])+Math.Sin(ph2[p]))*e;
      }
      sh*=0.012;
      if(t>=nextTw){ twT=t; twF=1400+r.NextDouble()*1400; nextTw=t+3+r.NextDouble()*7; }
      double tw=0; if(twT>=0){ double x=t-twT; if(x<1.5) tw=Math.Sin(TAU*twF*x)*Math.Exp(-x*4.0)*(1-Math.Exp(-x*80))*0.02; }
      double dout=dbuf[di]; dlp+=0.25*(dout-dlp);
      dbuf[di]=sh+tw+dlp*0.6; di=(di+1)%dl;
      double sig=wind+sub+sh*0.7+tw+dlp*0.9;
      double y=sig-hpx+0.995*hp; hpx=sig; hp=y;   // dc block
      a[i]=y;
      eWind+=wind*wind; eSub+=sub*sub; eSh+=sh*sh; eTw+=tw*tw;
    }
    double[] o=new double[L];
    for(int i=0;i<L;i++){
      if(i<F){ double q=(double)i/F*Math.PI/2; o[i]=a[i]*Math.Sin(q)+a[i+L]*Math.Cos(q); } else o[i]=a[i];
    }
    double mx=0; for(int i=0;i<L;i++) mx=Math.Max(mx, Math.Abs(o[i]));
    double g=mx>0?peak/mx:1;
    byte[] pcm=new byte[L*2];
    for(int i=0;i<L;i++){ short s=(short)Math.Round(Math.Max(-1,Math.Min(1,o[i]*g))*32767); pcm[i*2]=(byte)(s&255); pcm[i*2+1]=(byte)((s>>8)&255); }
    Stats=String.Format("rms wind {0:F3}  sub {1:F3}  shimmer {2:F3}  twinkle {3:F4}  peak before gain {4:F3}",
      Math.Sqrt(eWind/n), Math.Sqrt(eSub/n), Math.Sqrt(eSh/n), Math.Sqrt(eTw/n), mx);
    return pcm;
  }
}
"@
$pcm=[Ambience]::Render($Rate, $Seconds, 4.0, $Seed, $Peak)
$fs=[IO.File]::Create($out); $bw=New-Object IO.BinaryWriter($fs); $A=[Text.Encoding]::ASCII
$bw.Write($A.GetBytes('RIFF')); $bw.Write([int32](36+$pcm.Length)); $bw.Write($A.GetBytes('WAVE'))
$bw.Write($A.GetBytes('fmt ')); $bw.Write([int32]16); $bw.Write([int16]1); $bw.Write([int16]1); $bw.Write([int32]$Rate); $bw.Write([int32]($Rate*2)); $bw.Write([int16]2); $bw.Write([int16]16)
$bw.Write($A.GetBytes('data')); $bw.Write([int32]$pcm.Length); $bw.Write($pcm); $bw.Close()
[Ambience]::Stats
"wrote $out  $((Get-Item $out).Length) bytes, $Seconds s mono $Rate Hz"
