<!doctype html>
<!-- template for fssite.py bottle application to show svg chart of measured/recorded values -->
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
    
  %setdefault('subtitle',"")
  %setdefault('xgrid',[100,300,500,700,900])
  %setdefault('ygrid',[50,183,317,450])
  %setdefault('xlbls',[1,2,3,4,5])
  %setdefault('curves',[{'stroke':"#0074d9",'qtyp':1,'ylbls':[10,14,18,22],'legend':'y','crv':"109,119 117,94.1 125,77.6 134,77.6 142,50 142,450 342,450 342,284 350,326 359,367 367,367 375,367 384,400 392,450 400,422 409,351 417,253 425,160 434,119 442,119 450,136 459,169 467,202 475,181 484,202 492,271 500,253 509,216 517,218 525,202 534,202 542,202 550,185 559,160 567,160 575,160 584,140 592,77.6 600,119 609,87.9 617,77.6 625,98.3 634,119 642,119 650,169 659,174 667,171 675,119 684,119 692,105 700,119 709,87.9 717,119 725,119 734,94.1 742,111 750,119 759,102 767,119 775,119 784,119 792,119 800,119 809,119 817,119 825,119 834,119 842,119 850,119 859,119 867,119 875,119 884,119 892,129 900,160" }])
  %setdefault('xaxlbl',"")
  %setdefault('yaxlbl',"")
  %setdefault('footer',"")
  %setdefault('ylbls',[10,14,18,22])

 </head>
 
 <body>  <!-- onload="initpage()"--> 
  <div class="headng">{{title}}
   <p id="subtitle"> {{subtitle}} </p>
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
  <rect class="grid" x="100" y="50" width="800" height="400"> </rect>

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
   <i>{{!footer}}</i>
  </body>
</html>