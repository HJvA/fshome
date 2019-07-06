
<form method="post" action="/menu" id="mmenu" >
 <div class="hidden" id="params">
   <input name="jdtill" id="jdtill" value={{jdtill}}>
   <input name="ndays" id="ndays" value={{ndays}}>
   <input name="cursorPos" id="cursorPos" value={{cursorPos}}>
   <input name="grQuantIds" id="grQuantIds" value={{grQuantIds}}>
 </div>
 <fieldset class="fields">
  <div class="menubar" id="menu">
%for dct in menitms:
 %if type(dct['cls']) is list:  # dropdown
  %if 'typ' in dct:             # multiple
   <div class="menuselect multiselect">
    <select name={{dct['nm']}} {{dct['typ']}} onfocus="onFocus(this);" onblur="onBlur(this);">
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
     <button type={{dct['cls']}}>{{dct['nm']}} </button>
   </div>
 %end
%end
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
 