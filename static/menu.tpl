
<form method="post" action="/menu" id="mmenu" >
 <input type="hidden" name="cursorPos" id="cursorPos" value={{taxPos}}>
 <input type="hidden" name="taxEnd" id="taxEnd" value={{taxEnd}}>
 <fieldset class="fields">
  <div class="menubar" id="menu">
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
 