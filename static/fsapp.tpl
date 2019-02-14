<!doctype html>
<!-- template for fssite.py bottle application to show svg chart of measured values -->
<html lang="en">
 <head>
     <link rel="stylesheet" type="text/css" href="styles.css">
     <TITLE>{{title}}</TITLE>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1"> 
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="format-detection" content="telephone=no">
  <script type="text/javascript">
   function initpage() {
    document.getElementById("swidth").value = screen.width;
   }
  </script>
    
  %setdefault('xgrid',[100,300,500,700,900])
  %setdefault('ygrid',[50,183,317,450])
  %setdefault('xlbls',[1,2,3,4,5])
  %setdefault('curves',[{'stroke':"#0074d9",'qtyp':1,'ylbls':[10,14,18,22],'crv':"M0,10 L0,12 L1,12.2 L2,12.3 L3,13 L4,13.1 L5,13.1 L6,13.3 L6,10Z"}])
  %setdefault('xaxlbl',"")
  %setdefault('yaxlbl',"")
  %setdefault('footer',"")
  
  %setdefault('ylbls',[10,14,18,22])
  %setdefault('scale',"200,-33")   # effWdt/xsiz,-effHgt/ysiz
  %setdefault('yofs',"780")        # 450 + ymin*yscl

 </head>
 
 <body>  <!-- onload="initpage()"--> 
  <div class="headng">{{title}}
  </div>
   
    <br/>
  % menu = include("static/menu.tpl")
    <br/>
<svg class="graph" xmlns="http://www.w3.org/2000/svg" height="300" width="100%" viewBox="0 0 1000 500" preserveAspectRatio="none" >      <!--
       16 => 50    scl=800/(5-1)=200   -400/(22-10)=-33
       10 => 450   450 = -10*scl + ofs => ofs = 780
       style="clip-path: url(#clpPth); "
       width:<input type="text" id="swidth" />
     -->
  <defs>
      <clipPath id="clpPth">
         <rect x="100" y="50" width="800" height="400"> </rect>
      </clipPath>
  </defs>
  <rect class="grid" x="100" y="50" width="800" height="400"> </rect>

  %for curve,side in zip(curves,[80,960,90,990]):
     <g class="surfaces" clip-path="url(#clpPth)">
     	%if curve['qtyp']==1:
     	 <path  fill="none" stroke={{curve['stroke']}} stroke-width="2.8" d="{{curve['crv']}}" />
     	%else:
       <polyline fill="none" stroke={{curve['stroke']}} stroke-width="1.8" points="{{curve['crv']}}" />
      %end
     </g>
     <g class="labels y-labels" stroke={{curve['stroke']}}>
       <text  x="-50%" y="2%" transform="rotate(270)">{{yaxlbl}}</text>       
       %for i in range(len(ygrid)):
         <text y="{{ygrid[i]}}" x="{{side}}">{{"{:{align}4.3g}".format(curve['ylbls'][-i-1], align='>' if side<400 else '<')}}</text>
       %end
     </g>
  %end
     
     <g class="grid x-grid" transform="ref(svg)" >
       %for x in xgrid:
        <line x1="{{x}}" x2="{{x}}" y1="50" y2="450"></line>
       %end
     </g>
     <g class="grid y-grid" id="yGrid" >
       %for y in ygrid[1:-1]:
        <line x1="100" x2="900" y1="{{y}}" y2="{{y}}"></line>    
       %end
     </g>
     <g class="labels x-labels" transform="ref(svg)">
       <text  x="50%" y="98%">{{xaxlbl}}</text>
       %for d in range(len(xgrid)-1):
         <text  x="{{(xgrid[d]+xgrid[d+1])/2}}" y="475">{{xlbls[d]}}</text>
       %end
     </g>
</svg>

<hr/>
   <i>{{!footer}}</i>
  </body>
</html>