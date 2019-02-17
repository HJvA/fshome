<!doctype html>

<html lang="en">
 <HEAD>
  <%
  setdefault('menitms',
  		[{'rf':'/action/home','nm':'home','cls':'submit'},
  		 {'rf':'/action/sel','nm':'source','cls':
  		   [{'nm':'kamer','cls':'sel'},
  		    {'nm':'zolder','cls':'sel'}]},
  		 {'rf':'/action/drop','typ':'multiple','nm':'quantities','cls':
  		   [{'nm':'humidity','cls':'sel'},
  		    {'nm':'temperature','cls':'sel'}]}])
  %>
  <link type="text/css" href="navbar.css" rel="stylesheet">
  <!--
  <script  type="text/javascript">
    (function(l){
       var i,s={touchend:function(){}};
       for(i in s)
         l.addEventListener(i,s)})
       (document); // sticky hover fix in iOS
  </script>
  -->
 </HEAD>
 <BODY>

  <form method="post" action="/menu" id="mmenu" >
   <fieldset>
   
  <div class="menubar" id="menu">
  <!--
   <div class="overlay" onclick="javascript:document.getElementById('mmenu').submit();">
    <a href="#"></a>
   </div>
 -->
%for dct in menitms:
 %if type(dct['cls']) is list:  # dropdown
  %if 'typ' in dct:             # multiple
   <div class="menuselect">
    <select name={{dct['nm']}} {{dct['typ']}}>
     %for lit in dct['cls']:
      <option value={{lit['nm']}} {{'selected' if lit['cls']=='sel' else ''}}>{{lit['nm']}}</option>
     %end
    </select>
   </div>
  %else:   # single select
   <div class="menuselect">
    <select name={{dct['nm']}} onchange='if(this.value != 0) { this.form.submit(); }'>
     %for lit in dct['cls']:
      <option value={{lit['nm']}} {{'selected' if lit['cls']=='sel' else ''}}>{{lit['nm']}}</option>
     %end
    </select>
   </div>
  %end
 %else:  # button
   <div class="menuitem">
     <button type={{dct['cls']}} hreff={{dct['rf']}}>{{dct['nm']}} </button>
   </div>
 %end
%end
   </div>
   </fieldset>
  </form>
 
 </BODY>
</html>