
<form method="post" action="/menu" id="mmenu" >
 <div class="hidden" id="params">
   <input name="cursorPos" type="text" id="cursorPos" value="{{cursorPos}}">
   <input name="ndays" type="text" id="ndays" value="{{ndays}}">
   <input name="jdtill" type="text" id="jdtill" value="{{jdtill}}">
   <input name="grQuantIds" type="text" id="grQuantIds" value='{{grQuantIds}}'>
   <input name="evtData" type="text" id="evtData" value='{{evtData}}'>
 </div>
 <fieldset class="fields">
  <div class="menubar" id="menu">
%for dct in menitms:
 %if type(dct['cls']) is list:  # dropdown
  %if 'typ' in dct:             # multiple
   <div class="menuselect multiselect">
    <select name="{{dct['nm']}}" {{dct['typ']}} onfocus="onFocus(this);" onblur="onBlur(this);">
     %for lit in dct['cls']:
      <option value="{{lit['nm']}}" {{'selected' if lit['cls']=='sel' else ''}}>{{lit['nm']}}</option>
     %end
    </select>
   </div>
  %else:   # single select
   <div class="menuselect">
    <select name="{{dct['nm']}}" onchange='if(this.value != 0) { this.form.submit(); }'>
     %for lit in dct['cls']:
      <option value="{{lit['nm']}}" {{'selected' if lit['cls']=='sel' else ''}}>{{lit['nm']}}</option>
     %end
    </select>
   </div>
  %end
 %else:  # button
   <div class="menuitem">
     <button type="{{dct['cls']}}">{{dct['nm']}} </button>
   </div>
 %end
%end
   <div class="menuitem">
     <input name="evtDescr" class="menuinput" id="evtDescr" value="comment">
   </div>
  </div>
 </fieldset>
 
 <div class="fields atbottom">
   <select id="statbar" class="busy">
    %for msg in statbar:
     <option>{{msg}}</option>
    %end
     <option>{{!footer}}</option>
   </select>
 </div>
 
</form>
 