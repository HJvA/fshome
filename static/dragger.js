


// send some values to the server
function sendData(data) {
  //console.log("send data:",data);
  var xhr = new XMLHttpRequest();
  xhr.open("POST", "/cursor", true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.onreadystatechange = function() {
    if (this.readyState == 4 && this.status == 200) {
      console.log("response:" + this.responseText);
      var myArr = JSON.parse(this.responseText);
      msg(" dd "+ myArr["dd"]);
    }
  };
  for (kelm in data) {
  	  data[kelm] = data[kelm].value;
  }
  console.log("sending ",JSON.stringify(data));
  xhr.send(JSON.stringify(data));
}
// if( isMobile.any() ) alert('Mobile');
//https://github.com/smali-kazmi/detect-mobile-browser
var isMobile = {
    Android: function() {
        return navigator.userAgent.match(/Android/i);
    },
    BlackBerry: function() {
        return navigator.userAgent.match(/BlackBerry/i);
    },
    iOS: function() {
        return navigator.userAgent.match(/iPhone|iPad|iPod/i);
    },
    Opera: function() {
        return navigator.userAgent.match(/Opera Mini/i);
    },
    Windows: function() {
        return navigator.userAgent.match(/IEMobile/i) || navigator.userAgent.match(/WPDesktop/i);
    },
    any: function() {
        return (isMobile.Android() || isMobile.BlackBerry() || isMobile.iOS() || isMobile.Opera() || isMobile.Windows());
    }
}
function readCookie(name) {
	var nameEQ = name + "=";
	var ca = document.cookie.split(';');
	for(var i=0;i < ca.length;i++) {
		var c = ca[i];
		while (c.charAt(0)==' ') c = c.substring(1,c.length);
		if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
	}
	return null;
}

// show status message in either html section or input
function msg(txt, append, destinId) {
	if (destinId==null)
		destinId='statbar';
	var statmsg = document.getElementById(destinId);
	if (statmsg==null) {
		console.log(txt);
		return;
	}
	statmsg.classList.add("stabilise");
	statmsg.classList.add("busy");
	var i = txt.indexOf('\f'); // form feed , clear screenX
	if (i>=0)
		txt = txt.substr(i);
   //	txt = (new Date()).toLocaleTimeString('en-GB',{weekday:'narrow', hour12:false}) + ;
	//txt=dateTimeFormat.format(new Date()) + ': ' + txt;
	console.log("msg:"+statmsg.tagName+":"+txt);

	if (statmsg.tagName=='SELECT') {		// add line to combo
		var opt = document.createElement('option');  
		//opt.value=txt;
		opt.innerHTML=txt;
		statmsg.appendChild(opt);
		statmsg.selectedIndex = statmsg.options.length-1;
		if (statmsg.options.length>10){
			var elm = statmsg.options[0];
			elm.parentNode.removeChild(elm);
			//console.log("remove elm " + elm);
		}
		//statmsg.style.background="yellow";
		setTimeout(function(){
			//statmsg.style.background="white";
			//statmsg.classList.remove("stabilise");
			statmsg.className = "";
		},5000);
	}
	else if (append && i<0) {
		//statmsg.value+=txt;
		statmsg.innerHTML += txt+'<br/>';
	}
	else {
		//statmsg.value = txt;
		statmsg.innerHTML = txt;
	}
	//if (stClass==null)
	//{return;}
}
function msgState(state, destinId) {
	if (destinId==null)
		destinId='statbar';
	var statmsg = document.getElementById(destinId);
	statmsg.className = state;
	//statmsg.classList.toggle(state);
}
function julday(cursPos,jdtill,ndays) {
  var jd = jdtill - (900 -cursPos)/800*ndays;
  var tm = (jd - 2440587.5) * 86400.0;
  var date = new Date(tm*1000);
  return date.getDate()+"-"+date.toLocaleTimeString();
}
function divDict(divElm) {
  lst={};
  var elms = divElm.getElementsByTagName("*");
  for (var i = 0; i < elms.length; i++) {
     lst[elms[i].id] = elms[i];
     console.log(elms[i].id,":",elms[i].value);
  }
  return lst;
}

// string formatting
//var str = "She {1} {0}{2} by the {0}{3}. {-1}^_^{-2}";
//str = str.format(["sea", "sells", "shells", "shore"]);
//She sells seashells by the seashore. {^_^}
String.prototype.format = function (args) {
			var str = this;
			return str.replace(String.prototype.format.regex, function(item) {
				var intVal = parseInt(item.substring(1, item.length - 1));
				var replace;
				if (intVal >= 0) {
					replace = args[intVal];
				} else if (intVal === -1) {
					replace = "{";
				} else if (intVal === -2) {
					replace = "}";
				} else {
					replace = "";
				}
				return replace;
			});
};
String.prototype.format.regex = new RegExp("{-?[0-9]+}", "g");

pageSwiper =function (ulElm, movElm, cParams){
	var 
		detecttouch = !!('ontouchstart' in window) || !!('ontouchstart' in document.documentElement) || !!window.ontouchstart || !!window.Touch || !!window.onmsgesturechange || (window.DocumentTouch && window.document instanceof window.DocumentTouch),
		startx = 0, // starting x coordinate of touch point
		starty=0,
		orgx=movElm.x1.baseVal.value,
		orgy=0,
		boxWidth=ulElm.offsetWidth*1.01,
		threshold=boxWidth*0.5,
		swiping=false,
		pinching=false,
		ismousedown = false,
		params = cParams,
		moveElm=movElm;	
		//moveElm.x1.baseVal.value = taxPos;
		//moveElm.x2.baseVal.value = taxPos;
		console.log("setup dragger mov:",movElm.id," tpos:", orgx," quants:",params['grQuantIds'])
		
	
	var handletouch = function(srcElm,trgElm){
			console.log("page change from %s to %s",srcElm.id,trgElm.id);
		};
		
		
	function setPos(movElm, distx) {
		if (!movElm.moving)	
			movElm.classList.remove("stabilise"); 
		movElm.moving=true;
		var yOffset=0;
		var transformAttr = ' translate(' + distx + ',' + yOffset + ')';
		var prm=divDict(params);
      movElm.setAttribute('transform', transformAttr); 
      msg("dd: "+julday(distx+orgx, prm["jdtill"].value, prm["ndays"].value));
	}
	function finaliseLi(dist){
		if (swiping){
		  moveElm.x1.baseVal.value = dist+orgx;
		  moveElm.x2.baseVal.value = dist+orgx;
		  moveElm.setAttribute("transform","null");
		  var ps = dist+orgx;
		  prm=divDict(params);
        prm["cursorPos"].value=dist+orgx;
        var ndays = prm["ndays"].value;
        msg("dd: "+julday(dist+orgx, prm["jdtill"].value, ndays));
		  sendData(prm);
		  moveElm.classList.add("stabilise");
		  //msg("cookie "+readCookie("FSSITE"));
		  moveElm.moving=false;
		}
		swiping=false;
		pinching=false;
	}
	//check whether threshold has been passed	
	function checkDistance(dist){
		if (Math.abs(dist)>threshold){
			return false;
		}
		return true;
	}
	ulElm.addEventListener('touchstart', function(e){
		orgx=moveElm.x1.baseVal.value;
		orgy=moveElm.y1.baseVal.value;
		startx=parseInt(e.touches[0].clientX);
		starty=parseInt(e.touches[0].clientY);
		if (e.touches.length > 1){
			pinching=true;
			startx = (startx-parseInt(e.touches[1].clientX));
			starty = (starty-parseInt(e.touches[1].clientY));
		}
		else {
			swiping=true;
		}
				
		//e.preventDefault(); // prevent default click behavior
		msg("touch start " + startx + " box "+starty+" lis "+movElm.style.left)
		console.log("touchstart:%d, %d, %s",startx,starty,movElm.style.left);
	}, false);
	
	ulElm.addEventListener('touchmove', function(e){
		var touchobj = e.changedTouches[0]; // reference first touch point for this event
		if (swiping){
			var dist = parseInt(touchobj.clientX) - startx // calculate dist traveled by touch point
			if ( checkDistance(dist)){
				setPos(moveElm, dist);		
			} else {
				finaliseLi(dist);
			}
		}
		e.preventDefault();  //prevent default click behavior
		e.stopPropagation();
	}, false);
	
	ulElm.addEventListener('touchend', function(e){
		if (swiping || pinching){
		  var touchobj = e.changedTouches[0]; // reference first touch point for this event
		  var dist = parseInt(touchobj.clientX) - startx; // calculate dist traveled by touch point
		  checkDistance(dist);
		  finaliseLi(dist);
		}
	},false);
	
	if (!detecttouch){
		document.body.addEventListener('mousedown', function(e){
			if ( isContained(box2, e) ){
				var touchobj = e; // reference first touch point
				boxleft =movElm.offsetLeft;// parseInt(box2.style.left) // get left position of box
				startx = parseInt(touchobj.clientX) // get x coord of touch point
				ismousedown = true
				e.preventDefault() // prevent default click behavior
			}
		}, false)
		
		document.body.addEventListener('mousemove', function(e){
			if (ismousedown){
				var touchobj = e; // reference first touch point for this event
				dist = parseInt(touchobj.clientX) - startx; // calculate dist traveled by touch point
				ismousedown=checkDistance(dist);
			}
			if (ismousedown){
				var pos = boxleft + dist;
				//setPos(lis[actli], pos);
				setPos(moveElm, pos);
			} else {
				finaliseLi(0);
			}
			e.preventDefault();
		}, false)
		
		document.body.addEventListener('mouseup', function(e){
			if (ismousedown){
				var touchobj = e // reference first touch point
				
				dist = parseInt(touchobj.clientX) - startx // calculate dist traveled by touch point
				checkDistance(dist);
				finaliseLi(0);
			}
			e.preventDefault() // prevent default click behavior
		}, false)
	}
}
