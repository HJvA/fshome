<!doctype html>
<!-- template for fssite.py bottle application to show svg chart of measured/recorded values -->
<html lang="en">
 <head>
  <link rel="stylesheet" type="text/css" href="styles.css">
  <link type="text/css" href="navbar.css" rel="stylesheet">

  <TITLE>{{title}}</TITLE>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1"> 
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="format-detection" content="telephone=no">
  
  %setdefault('subtitle',"nothing worth saving")
  %setdefault('xgrid',[100,300,500,700,900])
  %setdefault('ygrid',[50,183,317,450])
  %setdefault('xlbls',['morning', 'after noon', 'evening', 'night'])
  %setdefault('curves',[{'selq': 'temperature', 'qtyp': 0, 'legend': 'rubbish', 'crv': [' 101,450 87,417 142,460 167,450 184,383 192,350 201,317 226,217 242,183 251,150 276,150 292,117 301,150 326,117 367,50 401,83.3 409,83.3 417,117', ' 867,217 884,117 892,83.3 901,50'], 'stroke': '#1084e9', 'ylbls': ['19.8 ', '20.2 ', '20.6 ', '  21 ']}])
  %setdefault('xaxlbl',"")
  %setdefault('yaxlbl',"")
  %setdefault('footer',"")
  %setdefault('ylbls',[10,14,18,22])
  %setdefault('taxEnd',2458637)
  %setdefault('taxPos',900)
  
  <script type="text/javascript" src="dragger.js"></script>
  <script type="text/javascript">
   function onLoad() {
    var touchBox=document.getElementById('plotarea');
    var movElm=document.getElementById('xcursor'); 
    var posVal=document.getElementById('cursorPos');
	 var swip = new pageSwiper(touchBox,movElm,posVal, {{taxEnd}}, {{taxPos}});
  }
  </script>
    
 </head>
 
 <body onload="onLoad();">
  <div class="headng">{{title}}
    <p> {{subtitle}} </p>
  </div>  
    <br/>
    %menu = include("static/menu.tpl")
    <br/>

 <svg class="graph" xmlns="http://www.w3.org/2000/svg" height="300" width="98%" viewBox="0 0 1000 500" preserveAspectRatio="none" >    
  <!--
  	style="border: 8px solid #cccccc; border-radius: 20px "
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
  <rect id="plotarea" class="grid" x="100" y="50" width="800" height="400"> </rect>
  <line id="xcursor" class="cursor" x1="110" y1="50" x2="110" y2="450"> </line>

  %for curve,side,xleg in zip(curves,[94,906,44,956],[300,500,100,700]):
     <g class="surfaces" clip-path="url(#clpPth)">
     	%if curve['qtyp']==1:
     	 <path  fill="none" stroke={{curve['stroke']}} stroke-width="2.8" d="{{curve['crv']}}" />
     	%else:
     	  %for crv in curve['crv']:
         <polyline fill="none" stroke={{curve['stroke']}} stroke-width="1.8" points="{{crv}}" />
        %end
      %end
     </g>
     <g class="labels y-labels" stroke={{curve['stroke']}}>
       <text  x="-50%" y="2%" transform="rotate(270)">{{yaxlbl}}</text>       
       %for i in range(len(ygrid)):
         <text y="{{ygrid[i]}}" x="{{side}}" text-anchor="{{'start' if side>400 else 'end'}}"> {{curve['ylbls'][-i-1]}}  </text>
       %end
     </g>
     <g class="labels legend" stroke={{curve['stroke']}}>
      <text  x="{{xleg+30}}" y="28" >{{curve['legend']}}</text>       
		<path stroke-width="2" d="M{{xleg}} 26 h26 Z" />
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
 <div class="fields atbottom">
   <select id="status" class="busy">
      <option><i>{{!footer}}</i></option>
   </select>
 </div>
</body>
</html>