


function onPageChangeExample(srcElm,trgElm) {
	console.log("page change from %s to %s",srcElm.id,trgElm.id);
	if (srcElm.id=="cryp" || trgElm.id=="cryp"){
		var i;
		var trg="";
		var src=srcElm.textContent; 
		//if (srcElm.id=="cryp")
		//	src=decodeURIComponent(src);
		for (i=0; i<src.length; i++)
			trg += String.fromCharCode(src.charCodeAt(i) ^ 0x001c);
		//if (trgElm.id=="cryp")
		//	trg=encodeURIComponent(trg);
		trgElm.textContent=trg;
	}
	else if (srcElm.id=="html" && trgElm.id=="rich")
		trgElm.innerHTML=srcElm.textContent;
	else if (srcElm.id=="rich" && trgElm.id=="html") {
		trgElm.textContent=srcElm.innerHTML;
	}
}

// send some values to the server
function sendData(data) {
  console.log("send data:",data);
  var xhr = new XMLHttpRequest();
  xhr.open("POST", "/cursor", true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.onreadystatechange = function() {
    if (this.readyState == 4 && this.status == 200) {
      console.log("response:" + this.responseText)
      var myArr = JSON.parse(this.responseText);
      msg("response "+ JSON.stringify(myArr));
    }
  };
  xhr.send(JSON.stringify(data));
}

// show status message in either html section or input
function msg(txt, append, destinId) {
	if (destinId==null)
		destinId='status';
	var statmsg = document.getElementById(destinId);
	if (statmsg==null) {
		console.log(txt);
		return;
	}
	
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
		statmsg.style.background="yellow";
		setTimeout(function(){
			statmsg.style.background="white";
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
		destinId='status';
	var statmsg = document.getElementById(destinId);
	statmsg.className = state;
	//statmsg.classList.toggle(state);
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



pageSwiper =function (ulElm, movElm, cPosElm, jdtill, taxPos, pageChanger){
	var 
		detecttouch = !!('ontouchstart' in window) || !!('ontouchstart' in document.documentElement) || !!window.ontouchstart || !!window.Touch || !!window.onmsgesturechange || (window.DocumentTouch && window.document instanceof window.DocumentTouch),
		boxleft, // left position of moving box
		movorgx,
		startx, // starting x coordinate of touch point
		dist = 0, // distance traveled by touch point
		boxWidth=ulElm.offsetWidth*1.01,
		threshold=boxWidth*0.5,
		swiping=false,
		ismousedown = false,
		tEnd=jdtill,
		PosValElm = cPosElm,
		moveElm=movElm;	
		moveElm.x1.baseVal.value = taxPos;
		moveElm.x2.baseVal.value = taxPos;
		console.log("setup dragger mov:",movElm.id," pos:", cPosElm.id," tend:",jdtill," tpos:", taxPos)
		
	
	var handletouch = pageChanger || function(srcElm,trgElm){
			console.log("page change from %s to %s",srcElm.id,trgElm.id);
		};

	var lis = ulElm.getElementsByTagName("li");
	if (lis.length==0){
	  lis = [ulElm]; 
	}
	//finaliseLi(actli);
		
	function setPos(movElm, pxPos) {
		//var scale =(upVal-lowVal)/boxWidth;
		//if (boxElm.style.left==null)
		if (!movElm.moving)	
			movElm.classList.remove("stabilise"); 
		movElm.moving=true;
		//movElm.style.left = pxPos + 'px';
		var yOffset=0;
		var transformAttr = ' translate(' + pxPos + ',' + yOffset + ')';
      movElm.setAttribute('transform', transformAttr); 
		msg("setPos " + pxPos);
	}
	function finaliseLi(li){
		moveElm.x1.baseVal.value = dist+movorgx;
		moveElm.x2.baseVal.value = dist+movorgx;
		moveElm.setAttribute("transform","null");
		//var cPosElm = document.getElementById('cursorPos');
		var ps = dist+movorgx;
		PosValElm.value = ps.toString();
		
		sendData({"pos":dist+movorgx,"tEnd":tEnd})
		moveElm.classList.add("stabilise");
		//console.log("li:%d ncls:%d",i,lis[i].classList.length);
		moveElm.moving=false;
		swiping=false;
	}
	//check whether threshold has been passed	
	function checkDistance(dist){
		if (Math.abs(dist)>threshold){
			return false;
		}
		return true;
	}
	ulElm.addEventListener('touchstart', function(e){
		var touchobj = e.changedTouches[0]; // reference first touch point
		boxleft=moveElm.offsetLeft;
		if (boxleft === undefined){
		  boxleft=0; //moveElm.x1.baseVal.value;
		}
		startx = parseInt(touchobj.clientX); // get x coord of touch point
		movorgx = moveElm.x1.baseVal.value;
		dist=0;
		swiping=true;
		//e.preventDefault(); // prevent default click behavior
		msg("touch start " + startx + " box "+boxleft+" lis "+movElm.style.left)
		console.log("touchstart:%d, %d, %s",boxleft,startx,movElm.style.left);
	}, false);
	
	ulElm.addEventListener('touchmove', function(e){
		var touchobj = e.changedTouches[0]; // reference first touch point for this event
		if (swiping){
			dist = parseInt(touchobj.clientX) - startx // calculate dist traveled by touch point
			swiping = checkDistance(dist);
		
			if (swiping){
				var pos = movorgx + dist;
				//setPos(lis[actli], pos);
				setPos(moveElm, dist);		
			} else {
				finaliseLi(0);
			}
		}
		e.preventDefault();  //prevent default click behavior
		e.stopPropagation();
	}, false);
	
	ulElm.addEventListener('touchend', function(e){
		if (!swiping)
			return;
		var touchobj = e.changedTouches[0]; // reference first touch point for this event
		dist = parseInt(touchobj.clientX) - startx; // calculate dist traveled by touch point
		checkDistance(dist);
		finaliseLi(0);
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
