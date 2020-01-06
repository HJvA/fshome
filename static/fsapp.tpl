<!doctype html>
<!-- template for fssite.py bottle application to show svg chart of measured/recorded values -->
<html lang="en">
 <head>
  <link rel="stylesheet" type="text/css" href="styles.css">
  <link type="text/css" href="navbar.css" rel="stylesheet">
  <link rel="apple-touch-icon" sizes="180x180" href="fshome.png">

  <TITLE>{{title}}</TITLE>
  <!--
  <meta http-equiv="refresh" content="5; url=/" > 
  -->
  <meta charset="UTF-8">
  <meta name="apple-mobile-web-app-title" content="fsHome hjva" />
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no"> 
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
  <meta name="format-detection" content="telephone=no">
  
  %setdefault('subtitle',"nothing worth saving")
  %setdefault('xgrid',[100,300,500,700,900])
  %setdefault('ygrid',[50,183,317,450])
  %setdefault('xlbls',['morning', 'after noon', 'evening', 'night'])
  %setdefault('curves',[{'selq': 'temperature', 'qtyp': 0, 'legend': 'rubbish', 'crv': [' 101,450 87,417 142,460 167,450 184,383 192,350 201,317 226,217 242,183 251,150 276,150 292,117 301,150 326,117 367,50 401,83.3 409,83.3 417,117', ' 867,217 884,117 892,83.3 901,50'], 'stroke': '#1084e9', 'ylbls': ['19.8 ', '20.2 ', '20.6 ', '  21 ']}])
  %setdefault('xaxlbl',"")
  %setdefault('yaxlbl',"")
  %setdefault('footer',"")
  %setdefault('jdtill',2458637.0)
  %setdefault('ndays',1.0)
  %setdefault('cursorPos',900)
  %setdefault('evtData',{})
  %setdefault('statbar',[])
  
  <script type="text/javascript" src="dragger.js"></script>
  <script type="text/javascript">
   function onLoad() {
    var touchBox=document.getElementById('plotarea');
    var movElm=document.getElementById('xcursor'); 
    //var grQuants={{[curve['legend'] for curve in curves]}};
    var params=document.getElementById('params');
    var evtDescr=document.getElementById('evtDescr');
	 var swip = new pageSwiper(touchBox,movElm,evtDescr,params);
  }
  function onFocus(elm){
   if (!isMobile.any()) {
    console.log("focus" + elm.style.height);
    elm.parentNode.style.height = '200px'; 
    elm.style.display = 'table-cell';
    }
  }
  function onBlur(elm){
   elm.parentNode.style.height = '3em';
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

 <svg class="graph" xmlns="http://www.w3.org/2000/svg" height="calc( 94vh - 16em )" width="98%" viewBox="0 0 1000 500" preserveAspectRatio="none" >    
  
  <defs>
      <clipPath id="clpPth">
         <rect x="100" y="50" width="800" height="400"> </rect>
      </clipPath>
  </defs>
  <rect id="plotarea" class="grid" x="100" y="50" width="800" height="400"> </rect>
  <line id="xcursor" class="cursor" x1="900" y1="42" x2="900" y2="458"> </line>

  %for curve,side,xleg in zip(curves,[98,906,44,956],[300,500,100,700]):
     <g class="surfaces" clip-path="url(#clpPth)">
      %if curve['qtyp']==1:
       <path  fill="none" stroke={{curve['stroke']}} stroke-opacity="0.7" stroke-width="2.8" d="{{curve['crv']}}" />
      %else:
        %for crv in curve['crv']:
         <polyline fill="none" stroke={{curve['stroke']}} stroke-width="1.8" points="{{crv}}" />
        %end
      %end
     </g>
     <g class="labels y-labels" fill={{curve['stroke']}} >
       <text  x="-50%" y="2%" transform="rotate(270)">{{yaxlbl}}</text>       
       %for i in range(len(ygrid)):
         <text y="{{ygrid[i]}}" x="{{side}}" text-anchor="{{'start' if side>400 else 'end'}}"> {{curve['ylbls'][-i-1]}}  </text>
       %end
     </g>
     <g class="labels legend" fill={{curve['stroke']}} >
      <text  x="{{xleg+30}}" y="28" >{{curve['legend']}}</text>       
      <path stroke-width="3" stroke={{curve['stroke']}} d="M{{xleg}} 26 h26 Z" />
     </g>
  %end
    
     <g class="grid x-grid"  >
       %for x in xgrid:
        <line x1="{{x}}" x2="{{x}}" y1="50" y2="450"></line>
       %end
     </g>
     <g class="grid y-grid" id="yGrid" >
       %for y in ygrid[1:-1]:
        <line x1="100" x2="900" y1="{{y}}" y2="{{y}}"></line>    
       %end
     </g>
     <g class="labels x-labels" >
       <text  x="50%" y="98%">{{xaxlbl}}</text>
       %for d in range(len(xgrid)-1):
         <text  x="{{(xgrid[d]+xgrid[d+1])/2}}" y="475">{{xlbls[d]}}</text>
       %end
     </g>
 </svg>


</body>
</html>