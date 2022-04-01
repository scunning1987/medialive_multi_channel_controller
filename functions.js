// multiviewer

//const apiendpointurl = "https://jl66fjfil5.execute-api.us-west-2.amazonaws.com/eng/playout"

//// LEAVE CODE BELOW THIS LINE /////

/* how to get the url to the base api gateway proxy
  page_url_to_array = window.location.href.split("/")
  api_gw_proxy_base = page_url_to_array.slice(0,5).join("/")
*/
var supervisor_pass = "dish";

function tableCreate(total_channels){

    document.getElementById("multiviewer").innerHTML = ""

    page_url_to_array = window.location.href.split("/")
    api_gw_proxy_base = page_url_to_array.slice(0,5).join("/")

    var body = document.body,
        tbl  = document.createElement('table'),

    columns = 8 / thumbnail_size;
    thumb_height = 90 * thumbnail_size;
    thumb_width = 160 * thumbnail_size;
    tbl.style.width  = '100px';
    tbl.style.padding = '20px';
    rows_required = Math.ceil(total_channels / columns);

    for(var i = 1; i <= rows_required; i++){
        var tr = tbl.insertRow();
        for(var j = 1; j < total_channels + 1; j++){
            if( Math.ceil( j / columns ) == i ){
                var td = tr.insertCell();
                proxy_thumbnail_https = live_event_map[j-1].jpg_url
                console.log("jpg url : " + proxy_thumbnail_https)
                td.innerHTML = '<img height="'+thumb_height+'" width="'+thumb_width+'" class="thumbs" id="thumb_jpg_'+(j-1).toString()+'" src="'+proxy_thumbnail_https+'" onclick=\'thumbclick("'+(j-1).toString()+'")\'></br>'+live_event_map[j-1].mux_channel_name
                td.id = "thumb_"+ (j-1).toString()
                //td.style.border = '1px solid black';
                td.style.padding = '10px 10px 10px 10px';
            }
        }
    }
    //document.body.appendChild(tbl)
    document.getElementById("multiviewer").appendChild(tbl);
}

function tableCreateForm(channel_list){
  var channels = 5;
  var columns = 7;
//  var rows_required = channels
  var row_head = [ "#","channel_name","input","frame_size","codec","program_name","program_number"]

  var body = document.body

    function generateTableHead(inputtable, row_head) {
      let thead = inputtable.createTHead();
      let row = thead.insertRow();
      for (var i = 0; i < row_head.length; i++) {
        let th = document.createElement("th");
        let text = document.createTextNode(row_head[i]);
        th.appendChild(text);
        th.style.border = '1px solid black';
        row.appendChild(th);
      }
    }

    var channel_size_dropdown = '<select><option value="hd">HD</option><option value="sd">SD</option></select>'
    var channel_codec_dropdown = '<select><option value="avc">AVC</option><option value="mpeg2">MPEG2</option></select>'
    var emx_flow_dropdown = ""
    var emx_flow_options = ""

    emx_flow_options += '<option value="CREATE">CREATE</option>'
    console.log("Flows to iterate through : " + mediaconnect_flow_list.length);
    for( var key in mediaconnect_flow_list ) {
        console.log("iterating through flow list : " + key)
        emx_flow_options += "<option value=" + mediaconnect_flow_list[key]['flow_arn']  + ">" + mediaconnect_flow_list[key]['flow_name'] + "</option>"
        }

    emx_flow_dropdown = '<select>'+emx_flow_options+'</select'
    console.log("dropdown : " + emx_flow_dropdown)
    function generateTable(inputtable, channel_list) {
      for (let element of channel_list) {
        let row = inputtable.insertRow();
        for (key in element) {
          let cell = row.insertCell();
          cell.style.border = '1px solid black';
          if ( element[key] == "DROP-SIZE" ) {
            cell.innerHTML = channel_size_dropdown;
          } else if ( element[key] == "DROP-CODEC" ) {
            cell.innerHTML = channel_codec_dropdown;
          } else if ( element[key] == "DROP-INPUT" ) {
            cell.innerHTML = emx_flow_dropdown;
          } else {
            let text = document.createTextNode(element[key]);
            cell.appendChild(text);
          }
        }
      }
    }

//"channel_input":"DROP-INPUT",
//"channel_size":"DROP-SIZE",
//"channel_codec":"DROP-CODEC",

  let inputtable = document.createElement('table');
  inputtable.id = "inputtable"
  //inputtable.style.border = '1px solid black';

  generateTableHead(inputtable, row_head);
  generateTable(inputtable, channel_list);
  document.getElementById("group_create_form").innerHTML = "";
  document.getElementById("group_create_form").appendChild(inputtable);

}

setInterval(function() {
// function to get updated thumbs from MediaLive channels - via S3
if ( multiviewer_status === "on" && groupSelector !== ""){
for (channel in live_event_map){
  var datevar = Date.now().toString()
  var proxy_thumbnail_https = live_event_map[channel].jpg_url
  document.getElementById('thumb_jpg_'+channel.toString()).src = proxy_thumbnail_https+'?rand='+datevar

  }
} else if ( multiviewer_status === "off" && pipSelector !== "" ) {

  for (channel in live_event_map){
    var datevar = Date.now().toString()
    var proxy_thumbnail_https = live_event_map[channel].jpg_url

    if ( pipSelector == channel ) {
                document.getElementById('channel_jpg_view').style.display = "inline-block";
                document.getElementById('channel_jpg_view').innerHTML = '<img height="360" class="ch-jpg-view" width=640 src='+proxy_thumbnail_https+'?rand='+datevar+'>'

              }
           }
}}, 2000);


function mediaLiveControl(evt, controlName) {
  var i, tabcontent, tablinks;
  tabcontent = document.getElementsByClassName("tabcontent");
  for (i = 0; i < tabcontent.length; i++) {
    tabcontent[i].style.display = "none";
  }
  tablinks = document.getElementsByClassName("tablinks");
  for (i = 0; i < tablinks.length; i++) {
    tablinks[i].className = tablinks[i].className.replace(" active", "");
  }
  document.getElementById(controlName).style.display = "block";
  evt.currentTarget.className += " active";

  // livestatic vodslate
  if ( controlName == "livestatic" ) {
    if ( pipSelector != "" ) {
      console.log("Selected tab is " + controlName + " need to run function to get available inputs/sources ")
      getLiveInputs(apiendpointurl)
    }
  } else if ( controlName == "vodslate" ) {
    console.log("Selected tab is " + controlName + " need to run function to get available inputs/sources ")
    // s3 api call
    s3getObjectsAPI(bucket, apiendpointurl)
  } else if (controlName == "group_ctrl"){

    document.querySelector('input[type=radio][name=create]:checked').checked = false;

    document.getElementById('copy-container').style.display = "none";
    document.getElementById('create-container').style.display = "none";
    document.getElementById('create-container-mux').style.display = "none";
    document.getElementById('group_create_form').innerHTML = "";
    document.getElementById('copy-container-mux').style.display = "none";

    console.log("Selected tab is " + controlName);

  } else if (controlName == "chstartstop") {
    document.getElementById("passwordbox").value = ""
  }  else {
    console.log("Selected tab is " + controlName)
  }
}

function chstartstopcontrol(action_type){
  console.log("Running Channel Start/Stop function")
  if ( pipSelector == "" ) {
    console.log("Operator has not selected a channel thumbnail. Select a thumbnail first before an action can be performed")
    alert("Please select a channel thumbnail first!")
  } else if (action_type == "stop" && document.getElementById("passwordbox").value != supervisor_pass ) {
    alert("For stop actions you must enter the supervisor password in the input field below... You have either not entered any value or the password is incorrect.")
  } else {
  if (window.confirm("Do you really want to "+action_type+" this channel?")) {

      document.getElementById(action_type).classList.add('pressedbutton');

//        var mediaconnect_flow_arns = {
//                  "ingress":live_event_map[pipSelector].mediaconnect_ingress_arn,
//                  "egress":live_event_map[pipSelector].mediaconnect_egress_arn
//                }
//        console.log(JSON.stringify(mediaconnect_flow_arns))
//        var mediaconnect_flow_arns_b64 = btoa(JSON.stringify(mediaconnect_flow_arns));

        // API Call to start/stop channel - proxy
        console.log("action type: "+action_type+" for channel ID : "+live_event_map[pipSelector].mux_channel_id)
        channelStartStop(action_type,live_event_map[pipSelector].mux_channel_id+":"+channel_groups[groupSelector].region,"mediaconnect_flow_arns_b64")
        console.log("action type: "+action_type+" for channel ID : "+live_event_map[pipSelector].ott_channel_id)
        channelStartStop(action_type,live_event_map[pipSelector].ott_channel_id+":"+channel_groups[groupSelector].region,"")


      // do EMX START STOP HERE
      // reset styling on the pip now that the action has been performed
      fadeAway(action_type)
    }
  }
}

function chliveswitch() {
  console.log("Running Live input switch function")
  if ( pipSelector == "" ) {
    console.log("Operator has not selected a channel thumbnail. Select a thumbnail first before an action can be performed")
    alert("Please select a channel thumbnail first!")
  } else {
  document.getElementById('live').classList.add('pressedbutton');
  input = document.getElementById("live_source_dropdown_select").value
  console.log("Switching to input: "+input+" for channel ID : "+live_event_map[pipSelector].mux_channel_id)
  emlSwitchAction(input, live_event_map[pipSelector].mux_channel_id + ":" + channel_groups[groupSelector].region, "", "immediateSwitchLive", "", 200, "master", "immediateswitch")
  emlSwitchAction(input, live_event_map[pipSelector].ott_channel_id + ":" + channel_groups[groupSelector].region, "", "immediateSwitchLive", "", 200, "master", "immediateswitch")

  }

  // reset styling on the pip now that the action has been performed
  fadeAway('live')
}

function chvodswitch(){
  console.log("Running VOD input switch function")

  if ( pipSelector == "" ) {
    console.log("Operator has not selected a channel thumbnail. Select a thumbnail first before an action can be performed")
    alert("Please select a channel thumbnail first!")
  } else {
   console.log("PipSelector value is : " + pipSelector);
   console.log("OTT channel id is : " + live_event_map[pipSelector]['ott_channel_id'] + ", and MUX channel id is : " + live_event_map[pipSelector]['mux_channel_id'])
  document.getElementById('vod').classList.add('pressedbutton');
  input = document.getElementById("vod_source_dropdown_select").value
  console.log("Switching to input: "+input+" for channel ID : "+live_event_map[pipSelector]['ott_channel_id'])
  emlSwitchAction(input, live_event_map[pipSelector]['mux_channel_id'] + ":" + channel_groups[groupSelector]['region'], bucket, "immediateSwitch", "", 200, "master", "immediateswitch")
  console.log("Switching to input: "+input+" for channel ID : "+live_event_map[pipSelector]['mux_channel_id'])
  emlSwitchAction(input, live_event_map[pipSelector]['ott_channel_id'] + ":" + channel_groups[groupSelector]['region'], bucket, "immediateSwitch", "", 200, "master", "immediateswitch")
  }

  fadeAway('vod')

}

function chbumperins(bumper_number){
  console.log("Running promo insert function")

  if ( pipSelector == "" ) {
    console.log("Operator has not selected a channel thumbnail. Select a thumbnail first before an action can be performed")
    alert("Please select a channel thumbnail first!")
  } else {
    console.log("Selected Channel ID : "+live_event_map[pipSelector].mux_channel_id)

    var selected_bumper_group = document.getElementById("bumper_groups_dropdown_select").value
    var bumpercount = Object.keys(bumper_groups[selected_bumper_group]["bumpers"]).length
    console.log("Found " + bumpercount + " promos in selected bumper group")

    // add pressed styling
    document.getElementById('insert'+bumper_number).classList.add('pressedbutton');

    bumper_to_play = bumper_groups[selected_bumper_group]["bumpers"][bumper_number-1]["s3uri"]
    console.log("Sending an API call to MediaLive to prep bumper : " + bumper_to_play)

    var s3_bumper_url = new URL(bumper_to_play.replace("s3://","https://"))
    var s3_bumper_bucket = s3_bumper_url.hostname
    var s3_bumper_key = s3_bumper_url.pathname.replace(/^\/+/, '')

    console.log("Bumper bucket : " + s3_bumper_bucket)
    console.log("Bumper key : " + s3_bumper_key)

    channelid = live_event_map[pipSelector].mux_channel_id + ":" + channel_groups[groupSelector].region
    console.log("Submitting API Call to prepare promo now")
    emlSwitchAction(s3_bumper_key, channelid, s3_bumper_bucket, "immediateContinue", "", 200, "master", "")

    // reset styling on the pip now that the action has been performed
    fadeAway('insert'+bumper_number);

    // remove prepare button pressed styling
    for (var i = 1; i <= bumpercount; i++) {
      fadeAway('prepare'+i+'')
    }
}

} // end chpromoins function

function chbumperprep(bumper_number){
  console.log("Running bumper prepare function")

  if ( pipSelector == "" ) {
    console.log("Operator has not selected a channel thumbnail. Select a thumbnail first before an action can be performed")
    alert("Please select a channel thumbnail first!")
  } else {
    console.log("Selected Channel ID : "+live_event_map[pipSelector].mux_channel_id)
    var selected_bumper_group = document.getElementById("bumper_groups_dropdown_select").value
    var bumpercount = Object.keys(bumper_groups[selected_bumper_group]["bumpers"]).length
    console.log("Found " + bumpercount + " bumpers in selected bumper group")

    // remove prepare button pressed styling
    for (var i = 1; i <= bumpercount; i++) {
      document.getElementById('prepare'+i+'').classList.remove('pressedbutton');
    }
    document.getElementById('prepare'+bumper_number).classList.add('pressedbutton');

    bumper_to_play = bumper_groups[selected_bumper_group]["bumpers"][bumper_number-1]["s3uri"]
    console.log("Sending an API call to MediaLive to prep bumper : " + bumper_to_play)

    var s3_bumper_url = new URL(bumper_to_play.replace("s3://","https://"))
    var s3_bumper_bucket = s3_bumper_url.hostname
    var s3_bumper_key = s3_bumper_url.pathname.replace(/^\/+/, '')

    console.log("Bumper bucket : " + s3_bumper_bucket)
    console.log("Bumper key : " + s3_bumper_key)

    channelid = live_event_map[pipSelector].mux_channel_id + ":" + channel_groups[groupSelector].region
    console.log("Submitting API Call to prepare bumper now")
    emlSwitchAction(s3_bumper_key, channelid, s3_bumper_bucket, "inputPrepare", "", 200, "master", "")
    }
}


var fadeAway = function(buttonid) {
  setTimeout(function(){

  if ( buttonid == "insertconfirmmessage" ){
    document.getElementById("insertconfirmmessage").display = "none";
    document.getElementById("insertconfirmmessage").innerHTML = "";
    console.log("hiding the button press message")
  } else {
  document.getElementById(buttonid).classList.remove('pressedbutton');
  }
 }, 4000);
}

function groupPopulator(value){
    groupSelector = value;
    pipSelector = ""
    document.getElementById('channel_jpg_view').style.display = "none";

    document.getElementById('channel_status').innerHTML = ""

    console.log("Selected group is " + groupSelector)

    window.live_event_map = channel_groups[groupSelector]['channels']

    var total_channels = live_event_map.length;
    console.log("There are " + total_channels.toString() + " channels in group: " + groupSelector)
    window.thumbnail_size = 1
    if ( parseInt(total_channels) < 9 ) {
      window.thumbnail_size = 2
    } else {
      window.thumbnail_size = 1
    }

    tableCreate(total_channels)

}

function thumbclick(channel_number) {
  // set Pip Selector value so it can be used by other functions
  pipSelector = channel_number.toString();

  // display multiviewer toggle button
  document.getElementById('togglemultiviewer').style.display = "inline-block"




  console.log("Channel " + pipSelector + " has been selected from the multiviewer")

  if ( pipSelector !== "" ) {
    channelState(pipSelector)
  }

    // Change display and size
    console.log("unhiding controls")
    document.getElementById('channel_status').style.display = "inline-block"
    document.getElementById('channel_control').style.display = "inline-block"
    document.getElementById('selected_channel_info').style.display = "inline-block"
    document.getElementById('multiviewer').style.display = "none"
    multiviewer_status = "off"
    document.getElementById('channels_body').classList.add('shrinkmultiviewer')
    document.getElementById('channels_body').classList.remove('expandmultiviewer')
    document.getElementById('togglecontrols').innerHTML = "Hide Controls"

  // Print channel information to channel info box
  // id to populate = channel_info
  document.getElementById("channel_info").innerHTML = '<p> Channel Name : '+live_event_map[pipSelector].mux_channel_name+' </p>'
  document.getElementById("channel_info").innerHTML += '<p> Channel ID : '+live_event_map[pipSelector].mux_channel_id+' </p>'
  document.getElementById("channel_info").innerHTML += '<p> AWS Region : '+channel_groups[groupSelector].region+' </p>'
  document.getElementById("channel_info").innerHTML += '<p><a target="_blank" href=https://hls-js.netlify.app/demo/?src='+live_event_map[pipSelector].ott_url+'>OTT Playback</a></p>'

  // if this channel is in a mux group, display channel and mux info
  if ( channel_groups[groupSelector]['mux_details']['total_rate'] > 0 ) {
    console.log("This group is a mux group. We will display mux data")
    document.getElementById("channel_info").innerHTML += '<h4> Group Mux Data</h4>'
    }

}


function inputPreview(bumper_number){
  console.log("Going to create presign url for Bumper " + bumper_number)
  var selected_bumper_group = document.getElementById("bumper_groups_dropdown_select").value
  bumper_s3uri = bumper_groups[selected_bumper_group]["bumpers"][bumper_number]["s3uri"]
  console.log("Promo S3 URI: " + bumper_s3uri)

  var s3_bumper_url = new URL(bumper_s3uri.replace("s3://","https://"))
  var s3_bumper_bucket = s3_bumper_url.hostname
  var s3_bumper_key = s3_bumper_url.pathname.replace(/^\/+/, '')

  var presign_url = presignGenerator(s3_bumper_bucket,s3_bumper_key);
  console.log("opening s3 URL: " + presign_url)
  window.open(presign_url,'_blank')

}

function pageLoadFunction(){

  getConfig()
  //console.log("channel start slate: "+ channel_start_slate)
  console.log("vod bucket: " + bucket)
  // var s3_slate_url = new URL(channel_start_slate.replace("s3://","https://")) -- deprecated
  //window.slate_bucket = s3_slate_url.hostname -- deprecated
  //window.startup_slate_key = s3_slate_url.pathname.replace(/^\/+/, '') -- deprecated

  // write deployment title
  deployment_name_pretty = "MediaLive Multi-Channel Controller"
  document.getElementById('deployment_title').innerHTML = '<h1 style="text-align:center">'+deployment_name_pretty+'</h1>'

//  var total_channels = Object.keys(live_event_map).length;
//    console.log("There are " + total_channels.toString() + " channels in this dashboard")
//    window.thumbnail_size = 1
//    if ( parseInt(total_channels) < 9 ) {
//      window.thumbnail_size = 2
//    } else {
//      window.thumbnail_size = 1
//    }

//    tableCreate(total_channels)

  // Populate the static dropdown elements with data obtained from the channel map json
//  bumperDropdownPopulate()

  // set channel selector and multiviewer status
  window.pipSelector = ""
  window.groupSelector = ""
  window.multiviewer_status = "on"

  console.log("pipSelector : " + pipSelector)
  console.log("groupSelector : " + groupSelector)
  console.log("multiviewer_status : " + multiviewer_status)

  // Hide Control headers until a selection is made
  document.getElementById('channel_status').style.display = "none"
  document.getElementById('channel_control').style.display = "none"
  document.getElementById('selected_channel_info').style.display = "none"
  document.getElementById('togglemultiviewer').style.display = "none"

}

function togglecontrols(){

    if ( document.getElementById('channel_control').style.display == "inline-block" && pipSelector == "" ) {
        console.log("hiding controls")
        document.getElementById('channel_status').style.display = "none"
        document.getElementById('channel_control').style.display = "none"
        document.getElementById('selected_channel_info').style.display = "none"
        document.getElementById('channels_body').classList.remove('shrinkmultiviewer')
        document.getElementById('channels_body').classList.add('expandmultiviewer')
        document.getElementById('togglecontrols').innerHTML = "View Controls"
        console.log("setting pip selector to 0")
        pipSelector = ""

    } else if (document.getElementById('channel_control').style.display == "inline-block" && pipSelector != "") {
       document.getElementById('channel_control').style.display = "none"
       document.getElementById('selected_channel_info').style.display = "none"
       document.getElementById('togglecontrols').innerHTML = "View Controls"

    } else if ( document.getElementById('channel_control').style.display == "inline-block" && pipSelector != "" ) {
        document.getElementById('channel_control').style.display = "inline-block"
        document.getElementById('selected_channel_info').style.display = "inline-block"
    } else {
        console.log("unhiding controls")
        document.getElementById('channel_status').style.display = "inline-block"
        document.getElementById('channel_control').style.display = "inline-block"
        document.getElementById('selected_channel_info').style.display = "inline-block"
        document.getElementById('channels_body').classList.add('shrinkmultiviewer')
        document.getElementById('channels_body').classList.remove('expandmultiviewer')
        document.getElementById('togglecontrols').innerHTML = "Hide Controls"
    }

}

function togglemultiviewer() {
  console.log("toggling multiviewer on")
  document.getElementById('channel_jpg_view').style.display = "none";
  pipSelector = ""


  // hide controls
    document.getElementById('channel_status').style.display = "none"
    document.getElementById('channel_control').style.display = "none"
    document.getElementById('selected_channel_info').style.display = "none"
    document.getElementById('channels_body').classList.remove('shrinkmultiviewer')
    document.getElementById('channels_body').classList.add('expandmultiviewer')
    document.getElementById('togglecontrols').innerHTML = "View Controls"
    document.getElementById('togglemultiviewer').style.display = "none"
    console.log("setting pip selector to 0")

  // display multiviewer
  document.getElementById('multiviewer').style.display = "inline"
  multiviewer_status = "on"


}

setInterval(function() {

  if ( pipSelector !== "" ) {
    channelState(pipSelector)
  }

}, 5000);

//setInterval(function() {
//
//    getConfig()
//
//}, 10000);

setInterval(function() {

    window.timenow = new Date().toTimeString()
    document.getElementById("clock").innerHTML = '<h4>'+timenow+'</h4>'

    //document.getElementById("clock").innerHTML = (hours + ":" + minutes + ":" + seconds + meridiem);

},1000)

function group_create_form_build(build_type){
  console.log("Building create form")

  // Clean the element up from any lingering forms
  document.getElementById('group_create_form').innerHTML = ""

  if ( build_type == "copy" ){
  console.log("Copy group was selected")
  } else {
  console.log("Create group was selected")
  // radio buttons for "mux", "mux+ott","ott"

  }
}

function group_copy_form_build(){
  console.log("Copy radio button selected");
  document.getElementById('copy-container').style.display = "inline";
  document.getElementById('create-container').style.display = "none";
  document.getElementById('create-container-mux').style.display = "none";
  document.getElementById('group_create_form').innerHTML = "";
  document.getElementById('group_create_button').style.display = "none";
  document.getElementById('copygroupname').value = "";
  document.getElementById('groupcopyselect').value = null;
  document.getElementById('group_create_form').innerHTML = "";
  document.getElementById('group_create_button').style.display = "none";

}

function group_create_form_build(){
  console.log("Create radio button selected");
  document.getElementById('copy-container').style.display = "none";
  document.getElementById('create-container').style.display = "inline";
  document.getElementById('newgroupname').value = "";
  document.getElementById('newgrouptype').value = "";
  document.getElementById('newgroupchannels').value = "";
  document.getElementById('group_create_form').innerHTML = "";
  document.getElementById('group_create_button').style.display = "none";
}

function newgrouptypeselect(selectedgrouptype){
  console.log("Group create type selected is : " + selectedgrouptype )

  if ( selectedgrouptype == "mux" || selectedgrouptype == "muxott" ) {
    document.getElementById('create-container-mux').style.display = "inline";

  } else {
  document.getElementById('create-container-mux').style.display = "none";
  document.getElementById('createmuxname').value = ""
  document.getElementById('createmuxrate').value = ""
  }
}

function creategrouptblgen(groupbuildtype) {

  document.getElementById('copy-container-mux').style.display = "none";
  document.getElementById('copymuxname').value = "";
  document.getElementById('copymuxrate').value = "";
  document.getElementById('group_create_form').innerHTML = "";

  listFlows()
  console.log(mediaconnect_flow_list)

  console.log("Group build type : " + groupbuildtype)
//  creategrouptblgen = this should be "copy" or "create"
  number_of_channels = document.getElementById('newgroupchannels').value
  if ( groupbuildtype == "create" ) {
    console.log("Group type to create: " + document.getElementById('newgrouptype').value)
    if ( document.getElementById('newgrouptype').value.length < 1 ) {
      alert("You need to select a Group Type first");
      document.getElementById('newgroupchannels').value = null;
    } else {
      console.log("Channels to create : " + number_of_channels)
      channel_list = []
      for(var i = 1; i <= number_of_channels; i++){
        const dict = {
         "channel_number":i,
         "channel_name":document.getElementById('newgroupname').value +'-'+ i.toString(),
         "channel_input":"DROP-INPUT",
         "channel_size":"DROP-SIZE",
         "channel_codec":"DROP-CODEC",
         "program_name":document.getElementById('newgroupname').value +'-'+ i.toString(),
         "program_id":i
        }
        channel_list.push(dict)
      }
      console.log("channnel list : " + JSON.stringify(channel_list))

    // Build json first, which will translate to table
    // {"#":n,"Ch. Name":"INPUT", "input":"DROPDOWN","frame_size":"","codec":"","prg. name":"","prg. id":""}

    // build the input table!
      tableCreateForm(channel_list)

      document.getElementById('group_create_button').style.display = "block";
      document.getElementById('group_create_button').style.margion = "10px";

    }
  } else if ( groupbuildtype == "copy" ) {

    grouptocopy = document.getElementById('groupcopyselect').value
    console.log("Going to build a copy table based on selected group")

    selected_group_details = channel_groups[grouptocopy]
    number_of_channels = selected_group_details['channels'].length

    mux_details = selected_group_details['mux_details']
    mux_rate = mux_details['total_rate']

    if ( mux_rate > 0 ) {
      console.log("We are copying a mux, unhide mux elements");
      document.getElementById('copy-container').style.display = "inline";
      document.getElementById('copy-container-mux').style.display = "inline";
    }

    console.log("Number of channels: " + number_of_channels)

    channel_list = []
    for (channel in selected_group_details['channels']) {
        i = parseInt(channel) + 1
        const dict = {
             "channel_number":i,
             "channel_name":document.getElementById('copygroupname').value +'-'+ i.toString(),
             "channel_input":"DROP-INPUT",
             "channel_size":selected_group_details['channels'][channel]['frame_size'],
             "channel_codec":selected_group_details['channels'][channel]['codec'],
             "program_name":document.getElementById('copygroupname').value +'-'+ i.toString(),
             "program_id":i
            }
            channel_list.push(dict)
          }
          console.log("channnel list : " + JSON.stringify(channel_list))

    // build the input table!
      tableCreateForm(channel_list)

      document.getElementById('group_create_button').style.display = "block";
      document.getElementById('group_create_button').style.margion = "10px";


    }




  }

function management_api () {
  function tableToJson(table) {
  var data = []; // first row needs to be headers
  var headers = [];
  for (var i=0; i<table.rows[0].cells.length; i++) {
   headers[i] = table.rows[0].cells[i].innerHTML.toLowerCase().replace(/ /gi,'');
  }
  // go through cells
  for (var i=1; i<table.rows.length; i++) {
    var tableRow = table.rows[i]; var rowData = {};
    for (var j=0; j<tableRow.cells.length; j++) {
      if ( tableRow.cells[j].innerHTML.includes('select') ) {
        var e = tableRow.cells[j].getElementsByTagName("select")[0];
        var myValue = e.options[e.selectedIndex].value;
        console.log("dropdown value : " + myValue)
        rowData[ headers[j] ] = myValue;
      } else {
        rowData[ headers[j] ] = tableRow.cells[j].innerHTML
     }
    }
    muxparams = {
            "program_name": "",
            "program_number": "",
            "service_name": "",
            "provider_name": "",
            "min_bitrate": "",
            "max_bitrate": "",
            "cbr": "",
            "priority": ""
    }
    rowData['mux_params'] = muxparams;
    data.push(rowData);
  }
  return data;
  }

  input_create_table = document.getElementById("inputtable")
  group_channel_create_data = tableToJson(input_create_table)

  if ( document.getElementById("create_new_group").checked ) {
    muxname = document.getElementById("createmuxname").value
    muxrate = document.getElementById("createmuxrate").value
    var e = document.getElementById("groupcreateregion");
    create_region = e.value;
    group_name = document.getElementById("newgroupname").value
    alert(document.getElementById("newgroupname").value)
    if ( parseInt(muxrate) > 0 ) {
      createmux = "True"
    } else {
      createmux = "False"
    }
  } else {
    muxname = document.getElementById("copymuxname").value
    muxrate = document.getElementById("copymuxrate").value
    var e = document.getElementById("groupcopyregion");
    create_region = e.value

    var e = document.getElementById("groupcreateregion");
    flow_region = e.value;

    group_name = document.getElementById("copygroupname").value
    if ( parseInt(muxrate) > 0 ) {
      createmux = "True"
    } else {
      createmux = "False"
    }
  }

  total_create_payload = {
    "copy": "",
    "mux": {
      "multiplex_name":muxname,
      "create": createmux,
      "bitrate": muxrate
    },
    "channels":group_channel_create_data
    }

  console.log(JSON.stringify(total_create_payload))
  groupCreate(total_create_payload,create_region,group_name)

}

/// API Calls
///
/// GROUP CREATE - START
///
function groupCreate(create_body,create_region,group_name){
    console.log("create body : " + JSON.stringify(create_body))

    channels_to_create = create_body['channels'].length
    grp_control_api_endpoint_url = apiendpointurl.replace("ctrl","workflow")

    var param1 = "task=create";
    var param2 = "&channels="+channels_to_create;
    var param3 = "&region="+create_region;
    var param4 = "&name="+group_name;
    var url = grp_control_api_endpoint_url+"?"+param1+param2+param3+param4
    console.log("channel start-stop-delete action api call - executing : " + url)

    var putReq = new XMLHttpRequest();
    putReq.open("PUT", url, true);
    putReq.setRequestHeader("Accept","*/*");
    putReq.setRequestHeader("Content-Type","application/json");
    putReq.send(JSON.stringify(create_body));

    if (putReq.status === 500 || putReq.status === 502) {
    console.log("Something went wrong")
    } else {
    //alert("Channel state is changing, please be patient. This may take 60-90 seconds")
    document.getElementById("insertconfirmmessage").display = 'block'
    document.getElementById("insertconfirmmessage").innerHTML = '<h4 style="color:red">Command executed: '+timenow+'</h4>'
    fadeAway("insertconfirmmessage")
    }
}
/// GROUP CREATE - END
///
/// GROUP CONTROL - START

function groupControlActions(group_action){

    if (groupSelector.length < 1){
      alert("Select a channel group first...");
      return;
    }
    console.log("channel start-stop-delete action api call: initializing")
    console.log("action to perform: " + group_action + " , on group : " + groupSelector)

    selected_group_region = channel_groups[groupSelector]['region']

    grp_control_api_endpoint_url = apiendpointurl.replace("ctrl","workflow")

    var param1 = "task="+group_action;
    var param2 = "&channels=";
    var param3 = "&region="+selected_group_region;
    var param4 = "&name="+groupSelector;
    var url = grp_control_api_endpoint_url+"?"+param1+param2+param3+param4
    console.log("channel start-stop-delete action api call - executing : " + url)

    var putReq = new XMLHttpRequest();
    putReq.open("PUT", url, true);
    putReq.setRequestHeader("Accept","*/*");
    putReq.send();

    if (putReq.status === 500 || putReq.status === 502) {
    console.log("Something went wrong")
    } else {
    //alert("Channel state is changing, please be patient. This may take 60-90 seconds")
    document.getElementById("insertconfirmmessage").display = 'block'
    document.getElementById("insertconfirmmessage").innerHTML = '<h4 style="color:red">Command executed: '+timenow+'</h4>'
    fadeAway("insertconfirmmessage")
    }
}

/// GROUP CONTROL - END
///
/// get Config START
function getConfig(){
  var json_data,
  current_url = window.location.href
  json_endpoint = current_url.substring(0,current_url.lastIndexOf("/")) + "/channel_map.json"

  // initialize dropdown options for channel group dropdown
  var input = document.getElementById("channel_group_dropdown_sel").value;
  let dropdown = document.getElementById('channel_group_dropdown_sel');
  let dropdown2 = document.getElementById('groupcopyselect');
  dropdown.length = 0;
  dropdown2.length = 0;

  let defaultOption = document.createElement('option');
  let defaultOption2 = document.createElement('option');
  defaultOption.text = 'Choose Channel Group';
  defaultOption2.text = 'Choose Channel Group';

  dropdown.add(defaultOption);
  dropdown2.add(defaultOption2);
  dropdown.selectedIndex = 0;
  dropdown2.selectedIndex = 0;


  var request = new XMLHttpRequest();
  request.open('GET', json_endpoint, false);

  request.onload = function() {

  if (request.status === 200) {
    const jdata = JSON.parse(request.responseText);
    console.log(jdata)
    window.channel_groups = jdata.channel_groups
    window.bucket = jdata.vod_bucket
    window.bumper_bucket_region = jdata.bumper_bucket_region
    window.apiendpointurl = jdata.control_api_endpoint_url
    window.apiendpointhost = jdata.control_api_endpoint_host_header
    window.bumper_groups = jdata.bumper_groups
    json_data = request.responseText

    let option;
    let option2;

    groups_list = Object.keys(channel_groups)

    for (let i = 0; i < groups_list.length; i++) {
      option = document.createElement('option');
      option2 = document.createElement('option');
      option.text = groups_list[i] //Object.keys(channel_groups)[i];
      option2.text = groups_list[i]
      option.value = groups_list[i] //Object.keys(channel_groups)[i];
      option2.value = groups_list[i]
      dropdown.add(option);
      dropdown2.add(option2);
    }

     } else {
    // Reached the server, but it returned an error
  }
}

request.onerror = function() {
  console.error('An error occurred fetching the JSON from ' + json_endpoint);
};

request.send();
return json_data
} // end

/// get Config END
///
/// presign Generator START
function presignGenerator(s3_promo_bucket,s3_promo_key){
    var presign_url;
    console.log("s3 presign generator api call: initializing")

    var param1 = "awsaccount=master";
    var param2 = "&functiontorun=presignGenerator"
    var param3 = "&channelid=0:x"; // this needs to be full list of channel id's and regions
    var param4 = "&maxresults=200";
    var param5 = "&bucket="+s3_promo_bucket;
    var param6 = "&input="+s3_promo_key;
    var param7 = "&follow=";
    var url = apiendpointurl+"?"+param1+param2+param3+param4+param5+param6+param7

    var request = new XMLHttpRequest();
    request.open('GET', url, false);

  request.onload = function() {

  if (request.status === 200) {
    var jdata = JSON.parse(request.responseText);

    console.log(jdata)
    presign_url = jdata.url

     } else {
    // Reached the server, but it returned an error
  }
}

request.onerror = function() {
  console.error('An error occurred fetching the JSON from ' + url);
  alert("Could not generate Presign S3 URL")
};

request.send();
return presign_url
} // end

/// presign Generator END
///
/// channel state START
function channelState() {
    console.log("channel state api call: initializing")

    var channellist = [];
    var channelid = live_event_map[pipSelector.toString()].mux_channel_id  + ":" + channel_groups[groupSelector].region

    var param1 = "awsaccount=master";
    var param2 = "&functiontorun=describeChannelState"
    var param3 = "&channelid="+channelid; // this needs to be full list of channel id's and regions
    var param4 = "&maxresults=200";
    var param5 = "&bucket=";
    var param6 = "&input=";
    var param7 = "&follow=";
    var url = apiendpointurl+"?"+param1+param2+param3+param4+param5+param6+param7

    var request = new XMLHttpRequest();
    request.open('GET', url, true);

    request.onload = function() {
      if (request.status === 200) {
        const state_data = JSON.parse(request.responseText);
        console.log("channel state api call response : " + JSON.stringify(state_data))
        document.getElementById('channel_status').innerHTML = '<h3>Channel Status: '+state_data.status+'</h3>'
       } else {
         error_message = "Unable to get channel status"
         document.getElementById('channel_status').innerHTML = '<h3>Channel Status: '+error_message+'</h3>'
        // Reached the server, but it returned an error
      }
    }
    request.onerror = function() {
      console.error('An error occurred fetching the JSON from ' + url);
    };

    request.send();
}

/// channel state END
///
/// GET MEDIACONNECT FLOWS - START
function listFlows() {
    console.log("list mediaconnnect flows: initializing")

    if(document.getElementById('create_new_group').checked) {
      var e = document.getElementById("groupcreateregion");
      flow_region = e.value;
    } else {
      var e = document.getElementById("groupcopyregion");
      flow_region = e.value;
    }
    console.log("getting flows in region : " + flow_region)

    var param1 = "awsaccount=master";
    var param2 = "&functiontorun=listFlows"
    var param3 = "&channelid=0:"+flow_region;
    var param4 = "&maxresults=200";
    var param5 = "&bucket=";
    var param6 = "&input=";
    var param7 = "&follow=";
    var url = apiendpointurl+"?"+param1+param2+param3+param4+param5+param6+param7
    console.log("Executing API Call to get MediaConnect flow list: " +url )

    var request = new XMLHttpRequest();
    request.open('GET', url, false);

    request.onload = function() {
      if (request.status === 200) {
        window.mediaconnect_flow_list = JSON.parse(request.responseText);
        console.log("MediaConnect Flow List: " + mediaconnect_flow_list)
       } else {
        // Reached the server, but it returned an error
      }
    }

    request.onerror = function() {
      console.error('An error occurred fetching the JSON from ' + url);
    };

    request.send();
}

/// GET MEDIACONNECT FLOWS - END
///
/// S3 GET OBJECT API CALL - START
function s3getObjectsAPI(bucket, apiendpointurl) {
    console.log("s3 get objects api call: initializing")
    var param1 = "awsaccount=master";
    var param2 = "&functiontorun=s3GetAssetList"
    var param3 = "&channelid=0:x";
    var param4 = "&maxresults=200";
    var param5 = "&bucket="+bucket;
    var param6 = "&input=";
    var param7 = "&follow=";
    var url = apiendpointurl+"?"+param1+param2+param3+param4+param5+param6+param7
    console.log("Executing API Call to get S3 assets: " +url )

    let dropdown = document.getElementById('vod_source_dropdown_select');
    dropdown.length = 0;

    let defaultOption = document.createElement('option');
    defaultOption.text = 'Choose Asset';

    dropdown.add(defaultOption);
    dropdown.selectedIndex = 0;

    var request = new XMLHttpRequest();
    request.open('GET', url, true);

    request.onload = function() {
      if (request.status === 200) {
        const data = JSON.parse(request.responseText);
        console.log("s3 get objects api call response: " + data)
        let option;
        for (let i = 0; i < data.length; i++) {
          option = document.createElement('option');
          option.text = data[i].name;
          option.value = data[i].key;
          dropdown.add(option);
        }
       } else {
        // Reached the server, but it returned an error
      }
    }

    request.onerror = function() {
      console.error('An error occurred fetching the JSON from ' + url);
    };

    request.send();
}

/// S3 GET OBJECT API CALL - END
///
/// Channel Map Poller - START

function channelMapPoller(apiendpointurl) {

    var input = document.getElementById("live_source_dropdown_select").value;
    let dropdown = document.getElementById('channel_group_dropdown_sel');
    dropdown.length = 0;

    let defaultOption = document.createElement('option');
    defaultOption.text = 'Choose Live Source';

    dropdown.add(defaultOption);
    dropdown.selectedIndex = 0;

    var request = new XMLHttpRequest();
    request.open('GET', url, true);

    request.onload = function() {
      if (request.status === 200) {
        const data = JSON.parse(request.responseText);
        console.log("get live inputs api call response : " + data)
        let option;
        for (let i = 0; i < data.length; i++) {
          option = document.createElement('option');
          option.text = data[i].name;
          option.value = data[i].name;
          dropdown.add(option);
        }
       } else {
        // Reached the server, but it returned an error
      }
    }
    request.onerror = function() {
      console.error('An error occurred fetching the JSON from ' + url);
    };

    request.send();
}

/// Channel Map Poller - END
///
/// EML GET ATTACHED INPUTS - START

function getLiveInputs(apiendpointurl) {
    console.log("get live inputs api call: initializing")
    console.log("pipSelector: " + pipSelector)
    var channelid = live_event_map[pipSelector].mux_channel_id + ":" + channel_groups[groupSelector].region;
    var input = document.getElementById("live_source_dropdown_select").value;

    var param1 = "awsaccount=master";
    var param2 = "&functiontorun=getAttachedInputs"
    var param3 = "&channelid="+channelid;
    var param4 = "&maxresults=200";
    var param5 = "&bucket=";
    var param6 = "&input="+input;
    var param7 = "&follow=";

    var url = apiendpointurl+"?"+param1+param2+param3+param4+param5+param6+param7
    console.log("Executing API call to get attached inputs to MediaLive Channel " + channelid )

    let dropdown = document.getElementById('live_source_dropdown_select');
    dropdown.length = 0;

    let defaultOption = document.createElement('option');
    defaultOption.text = 'Choose Live Source';

    dropdown.add(defaultOption);
    dropdown.selectedIndex = 0;

    var request = new XMLHttpRequest();
    request.open('GET', url, true);

    request.onload = function() {
      if (request.status === 200) {
        const data = JSON.parse(request.responseText);
        console.log("get live inputs api call response : " + data)
        let option;
        for (let i = 0; i < data.length; i++) {
          option = document.createElement('option');
          option.text = data[i].name;
          option.value = data[i].name;
          dropdown.add(option);
        }
       } else {
        // Reached the server, but it returned an error
      }
    }
    request.onerror = function() {
      console.error('An error occurred fetching the JSON from ' + url);
    };

    request.send();
}

/// EML GET ATTACHED INPUTS - END

/// EML SWITCH - START

function emlSwitchAction(file, chid, bucket, takeType, follow, maxresults, awsaccount, scte){
    console.log("eml switch action api call: initializing")
    console.log("Executing API PUT action for switch type "+takeType)

    var param1 = "awsaccount="+awsaccount;
    var param2 = "&functiontorun="+takeType
    var param3 = "&channelid="+chid;
    var param4 = "&maxresults="+maxresults;
    var param5 = "&bucket="+bucket;
    var param6 = "&input="+file;
    var param7 = "&follow="+follow;
    var param8 = "&duration="+scte;
    var url = apiendpointurl+"?"+param1+param2+param3+param4+param5+param6+param7+param8
    console.log("eml switch action api call - executing : "+url)

    var putReq = new XMLHttpRequest();
    putReq.open("PUT", url, true);
    putReq.setRequestHeader("Accept","*/*");
    putReq.send();
    var timenow = new Date().toTimeString()
    document.getElementById("insertconfirmmessage").display = 'block'
    document.getElementById("insertconfirmmessage").innerHTML = '<h4 style="color:red">Command executed: '+timenow+'</h4>'
    fadeAway("insertconfirmmessage")
}

/// EML SWITCH - END

/// EML SWITCH VOD - START

/// EML SWITCH VOD - END

/// EML CHANNEL START/STOP - START

function channelStartStop(startstop,channelid,flows){

    if (pipSelector.length < 1){
      alert("Select a channel first...");
      return;
    }
    console.log("channel start-stop action api call: initializing")


    var param1 = "awsaccount=master";
    var param2 = "&functiontorun=channelStartStop"
    var param3 = "&channelid="+channelid;
    var param4 = "&maxresults=200";
    var param5 = "&bucket=bucket:path/key.mp4";
    var param6 = "&input="+startstop;
    var param7 = "&follow="+flows;
    var param8 = "&duration=";
    var url = apiendpointurl+"?"+param1+param2+param3+param4+param5+param6+param7+param8
    console.log("channel start-stop action api call - executing : " + channelid)

    var putReq = new XMLHttpRequest();
    putReq.open("PUT", url, true);
    putReq.setRequestHeader("Accept","*/*");
    putReq.send();

    if (putReq.status === 500 || putReq.status === 502) {
    console.log("Something went wrong")
    } else {
    alert("Channel state is changing, please be patient. This may take 60-90 seconds")
    }
}

/// EML CHANNEL START/STOP - END
///


