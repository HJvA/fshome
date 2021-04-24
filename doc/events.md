# fshome events handling

each sampler device will have an events handler i.e. a signaller object
assigned by defSignaller
each sampler has a state setter handler function registered in the signaller
the signaller is generic class in fshome
that registers actions that must occur when a quantity event occurs in _signalDef
if an event occurs, all _handlers functions will be called till one returns True


