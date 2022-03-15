// multiviewer

//const apiendpointurl = "https://jl66fjfil5.execute-api.us-west-2.amazonaws.com/eng/playout"

//// LEAVE CODE BELOW THIS LINE /////

/* how to get the url to the base api gateway proxy
  page_url_to_array = window.location.href.split("/")
  api_gw_proxy_base = page_url_to_array.slice(0,5).join("/")
*/
supervisor_pass = "star"

function tableCreate(total_channels){

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
                //td.appendChild(document.createTextNode(thumbs[j-1]));
                proxy_thumbnail_s3uri = live_event_map[j.toString()].proxy_thumbnail_name
                proxy_thumbnail_https = api_gw_proxy_base + "/" + proxy_thumbnail_s3uri.replace("s3://","")
                td.innerHTML = '<img height="'+thumb_height+'" width="'+thumb_width+'" class="thumbs" id="thumb_jpg_'+j.toString()+'" src="'+proxy_thumbnail_https+'" onclick=\'thumbclick("'+j.toString()+'")\'></br>'+live_event_map[j.toString()].channel_friendly_name
                td.id = "thumb_"+ j.toString()
                //td.style.border = '1px solid black';
                td.style.padding = '10px 10px 10px 10px';
            }
        }
    }
    //document.body.appendChild(tbl)
    document.getElementById("multiviewer").appendChild(tbl);
}

setInterval(function() {
// function to get updated thumbs from MediaLive channels - via S3
if ( multiviewer_status == "on" ){
for (channel in live_event_map){
  var datevar = Date.now().toString()
  var proxy_thumbnail_s3uri = live_event_map[channel].proxy_thumbnail_name
  var proxy_thumbnail_https = api_gw_proxy_base + "/" + proxy_thumbnail_s3uri.replace("s3://","")
  document.getElementById('thumb_jpg_'+channel).src = proxy_thumbnail_https+'?rand='+datevar
  }
}
}, 2000);

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
  } else if (controlName == "bumper"){
    console.log("Selected tab is " + controlName)

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

        var mediaconnect_flow_arns = {
                  "ingress":live_event_map[pipSelector].mediaconnect_ingress_arn,
                  "egress":live_event_map[pipSelector].mediaconnect_egress_arn
                }
        console.log(JSON.stringify(mediaconnect_flow_arns))
        var mediaconnect_flow_arns_b64 = btoa(JSON.stringify(mediaconnect_flow_arns));

        // API Call to start/stop channel - proxy
        console.log("action type: "+action_type+" for channel ID : "+live_event_map[pipSelector].primary_channel_id)
        channelStartStop(action_type,live_event_map[pipSelector].primary_channel_id+":"+live_event_map[pipSelector].channel_region,mediaconnect_flow_arns_b64)
        console.log("action type: "+action_type+" for channel ID : "+live_event_map[pipSelector].proxy_gen_channel)
        channelStartStop(action_type,live_event_map[pipSelector].proxy_gen_channel+":"+live_event_map[pipSelector].channel_region,"")


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
  console.log("Switching to input: "+input+" for channel ID : "+live_event_map[pipSelector].primary_channel_id)
  channelid = live_event_map[pipSelector].primary_channel_id + ":" + live_event_map[pipSelector].channel_region
  emlSwitchAction(input, channelid, "", "immediateSwitchLive", "", 200, "master", "immediateswitch")
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
  document.getElementById('vod').classList.add('pressedbutton');
  input = document.getElementById("vod_source_dropdown_select").value
  console.log("Switching to input: "+input+" for channel ID : "+live_event_map[pipSelector].primary_channel_id)
  channelid = live_event_map[pipSelector].primary_channel_id + ":" + live_event_map[pipSelector].channel_region
  emlSwitchAction(input, channelid, bucket, "immediateSwitch", "", 200, "master", "immediateswitch")
  }

  fadeAway('vod')

}

function chbumperins(bumper_number){
  console.log("Running promo insert function")

  if ( pipSelector == "" ) {
    console.log("Operator has not selected a channel thumbnail. Select a thumbnail first before an action can be performed")
    alert("Please select a channel thumbnail first!")
  } else {
    console.log("Selected Channel ID : "+live_event_map[pipSelector].primary_channel_id)

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

    channelid = live_event_map[pipSelector].primary_channel_id + ":" + live_event_map[pipSelector].channel_region
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
    console.log("Selected Channel ID : "+live_event_map[pipSelector].primary_channel_id)
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

    channelid = live_event_map[pipSelector].primary_channel_id + ":" + live_event_map[pipSelector].channel_region
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

function bumperDropdownPopulate(){

  let dropdown = document.getElementById('bumper_groups_dropdown_select');
  dropdown.length = 0;

  let defaultOption = document.createElement('option');
  defaultOption.text = 'Select A League to Load Relevant Bumpers';
  defaultOption.value = ""

  dropdown.add(defaultOption);
  dropdown.selectedIndex = 0;

  for (var bumper_group in bumper_groups){
    option = document.createElement('option');
    option.text = bumper_group;
    option.value = bumper_group;
    dropdown.add(option)
  }

}

function bumperPopulator(value){

  var selected_bumper_group = value

  if ( value == "" ) {
    document.getElementById("bumperprepare").innerHTML = ""
    document.getElementById("bumperinsert").innerHTML = ""
    if (pipSelector == ""){
        console.log("No Channel selected, so clearing channel information box and printing Bumper links")
        document.getElementById("channel_info").innerHTML = ""
        document.getElementById("channel_info").innerHTML += '<h3> Bumper Videos </h3>'
          } else {
          document.getElementById("channel_info").innerHTML = ""
          document.getElementById("channel_info").innerHTML = '<p> Channel Name : '+live_event_map[pipSelector].channel_friendly_name+' </p>'
          document.getElementById("channel_info").innerHTML += '<p> Channel ID : '+live_event_map[pipSelector].primary_channel_id+' </p>'
          document.getElementById("channel_info").innerHTML += '<p> AWS Region : '+live_event_map[pipSelector].channel_region+' </p>'
          document.getElementById("channel_info").innerHTML += '<h3> Bumper Videos </h3>'
      }
  }  else {

      console.log("Populating bumper buttons with correct object url's for group " + selected_bumper_group)

      var bumpercount = Object.keys(bumper_groups[selected_bumper_group]["bumpers"]).length
      console.log("There are " + bumpercount + " bumpers for this selected group")
      document.getElementById("bumperprepare").innerHTML = ""
      document.getElementById("bumperinsert").innerHTML = ""
      // create buttons
      // input prepare / input switch
      for (var i = 1; i <= bumpercount; i++) {
        document.getElementById("bumperprepare").innerHTML += '<button class="bumper_buttons bumper bumper_prepare" id="prepare'+i+'" onclick="chbumperprep('+i+')">Prepare '+i+'</button>'
        document.getElementById("bumperinsert").innerHTML += '<button class="bumper_buttons bumper bumper_insert" id="insert'+i+'" onclick="chbumperins('+i+')">Insert '+i+'</button>'
      }
      if (pipSelector == ""){
        console.log("No Channel selected, so clearing channel information box and printing Bumper links")
        document.getElementById("channel_info").innerHTML = ""
        document.getElementById("channel_info").innerHTML += '<h3> Bumper Videos </h3>'
      } else {
      document.getElementById("channel_info").innerHTML = ""
      document.getElementById("channel_info").innerHTML = '<p> Channel Name : '+live_event_map[pipSelector].channel_friendly_name+' </p>'
      document.getElementById("channel_info").innerHTML += '<p> Channel ID : '+live_event_map[pipSelector].primary_channel_id+' </p>'
      document.getElementById("channel_info").innerHTML += '<p> AWS Region : '+live_event_map[pipSelector].channel_region+' </p>'
      document.getElementById("channel_info").innerHTML += '<h3> Bumper Videos </h3>'
      }

      for (var i = 1; i <= bumpercount; i++) {
        base0i = i - 1
        document.getElementById("channel_info").innerHTML += '<a href="#" onclick="inputPreview('+base0i+')" id="bumper'+i+'link">Bumper '+i+' : '+bumper_groups[selected_bumper_group]["bumpers"][base0i]["description"]+'</a></br>'
      }
  }

}

var sldpPlayers = [];

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
  document.getElementById("channel_info").innerHTML = '<p> Channel Name : '+live_event_map[pipSelector].channel_friendly_name+' </p>'
  document.getElementById("channel_info").innerHTML += '<p> Channel ID : '+live_event_map[pipSelector].primary_channel_id+' </p>'
  document.getElementById("channel_info").innerHTML += '<p> AWS Region : '+live_event_map[pipSelector].channel_region+' </p>'

  // Bumper Videos Links
  document.getElementById("channel_info").innerHTML += '<h3> Bumper Videos </h3>'
  if ( document.getElementById("bumper_groups_dropdown_select").value == "" ) {
    console.log("No bumper group has been selected from the dropdown menu, nothing to show")
  } else {
  console.log("printing S3 links for Bumper videos")
  var selected_bumper_group = document.getElementById("bumper_groups_dropdown_select").value
  var bumpercount = Object.keys(bumper_groups[selected_bumper_group]["bumpers"]).length
  for (var i = 1; i <= bumpercount; i++) {
      console.log("selected bumper group is : "+ selected_bumper_group)
      base0i = i - 1
      document.getElementById("channel_info").innerHTML += '<a href="#" onclick="inputPreview('+base0i+')" id="bumper'+i+'link">Bumper '+i+' : '+bumper_groups[selected_bumper_group]["bumpers"][base0i]["description"]+'</a></br>'
    }
  }

  // initialize the low latency players
  function startPlayers () {
        console.log("starting sdlp players, checking to see if they are loaded already....")

        if ( sldpPlayers.length > 0 ) {
          console.log("players were already loaded, sending to restart function")
          restartPlayers();
          doStart();
        } else {
          console.log("players not initialized, doing now....")
          doStart();
        }
      }

      function restartPlayers () {
        var destroyCnt = 0;
        for (var i = 0; i < sldpPlayers.length; i++) {
          sldpPlayers[i].destroy(function () {
            console.log("destroying current instance of player")
            destroyCnt++;
            if (destroyCnt == sldpPlayers.length) {
              sldpPlayers = [];
              doStart();
            }
          });
        }
      console.log("old instances of players have been removed.")
      }

      function doStart () {
        console.log("initializing new sdlp players")
        for (var i = 0; i < 2; i++) {
          var streamurl;
          if ( i == 0) {
            streamurl = live_event_map[pipSelector].low_latency_url_source
          } else {
            streamurl = live_event_map[pipSelector].low_latency_url_medialive
          }

          var player = SLDP.init({
            container:          'player-wrp-' + (i + 1),
            stream_url:         streamurl,
            buffering:          250,
            autoplay:           true,
            muted:              true,
            height:             360,
            width:              640,
            vu_meter:           {type: 'input', mode: 'peak', container: 'vu-meter-' + (i + 1), rate: 10},
          });
          sldpPlayers[i] = player;
        }
      console.log("done initializing low latency players.")
      }
  startPlayers()
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
  console.log("channel map : " + JSON.stringify(live_event_map))
  //console.log("channel start slate: "+ channel_start_slate)
  console.log("vod bucket: " + bucket)
  console.log("dashboard name: " + deployment_name)
  // var s3_slate_url = new URL(channel_start_slate.replace("s3://","https://")) -- deprecated
  //window.slate_bucket = s3_slate_url.hostname -- deprecated
  //window.startup_slate_key = s3_slate_url.pathname.replace(/^\/+/, '') -- deprecated

  // write deployment title
  var deployment_name_pretty = deployment_name.toUpperCase().replace("_"," ")
  document.getElementById('deployment_title').innerHTML = '<h1 style="text-align:center">'+deployment_name_pretty+'</h1>'

  var total_channels = Object.keys(live_event_map).length;
    console.log("There are " + total_channels.toString() + " channels in this dashboard")
    window.thumbnail_size = 1
    if ( parseInt(total_channels) < 9 ) {
      window.thumbnail_size = 2
    } else {
      window.thumbnail_size = 1
    }

    tableCreate(total_channels)

  // Populate the static dropdown elements with data obtained from the channel map json
  bumperDropdownPopulate()

  // set channel selector and multiviewer status
  pipSelector = ""
  multiviewer_status = "on"



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


        // destroying sldp players
        var destroyCnt = 0;
        if ( sldpPlayers.length > 0 ) {
            for (var i = 0; i < sldpPlayers.length; i++) {
              sldpPlayers[i].destroy(function () {
                console.log("destroying current instance of player")
                destroyCnt++;
              })
              }
        } else {
          console.log("No SLDP player to destroy")
        }
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

  // destroying sldp players
  var destroyCnt = 0;
  if ( sldpPlayers.length > 0 ) {
      for (var i = 0; i < sldpPlayers.length; i++) {
        sldpPlayers[i].destroy(function () {
          console.log("destroying current instance of player")
          destroyCnt++;
        })
        }
  } else {
    console.log("No SLDP player to destroy")
  }

  // display multiviewer
  document.getElementById('multiviewer').style.display = "inline"
  multiviewer_status = "on"


}

setInterval(function() {

  if ( pipSelector !== "" ) {
    channelState(pipSelector)
  }

}, 5000);

setInterval(function() {

    var timenow = new Date().toTimeString()
    document.getElementById("clock").innerHTML = '<h4>'+timenow+'</h4>'

    //document.getElementById("clock").innerHTML = (hours + ":" + minutes + ":" + seconds + meridiem);

},1000)

/// API Calls
///
/// get Config START
function getConfig(){
  var json_data,
  current_url = window.location.href
  json_endpoint = current_url.substring(0,current_url.lastIndexOf("/")) + "/channel_map.json"

  var request = new XMLHttpRequest();
  request.open('GET', json_endpoint, false);

  request.onload = function() {

  if (request.status === 200) {
    const jdata = JSON.parse(request.responseText);
    console.log(jdata)
    window.live_event_map = jdata.channel_map
    window.deployment_name = jdata.dashboard_title
    window.bucket = jdata.vod_bucket
    window.bumper_bucket_region = jdata.bumper_bucket_region
    window.apiendpointurl = jdata.control_api_endpoint_url
    window.apiendpointhost = jdata.control_api_endpoint_host_header
    window.bumper_groups = jdata.bumper_groups
    json_data = request.responseText
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
    var channelid = live_event_map[pipSelector].primary_channel_id  + ":" + live_event_map[pipSelector].channel_region

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
/// EML GET ATTACHED INPUTS - START

function getLiveInputs(apiendpointurl) {
    console.log("get live inputs api call: initializing")
    var channelid = live_event_map[pipSelector].primary_channel_id + ":" + live_event_map[pipSelector].channel_region;
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

function emlSwitchAction(file, channelid, bucket, takeType, follow, maxresults, awsaccount, scte){
    console.log("eml switch action api call: initializing")
    console.log("Executing API PUT action for switch type "+takeType)

    var param1 = "awsaccount="+awsaccount;
    var param2 = "&functiontorun="+takeType
    var param3 = "&channelid="+channelid;
    var param4 = "&maxresults="+maxresults;
    var param5 = "&bucket="+bucket;
    var param6 = "&input="+file;
    var param7 = "&follow="+follow;
    var param8 = "&duration="+scte;
    var url = apiendpointurl+"?"+param1+param2+param3+param4+param5+param6+param7+param8
    console.log("eml switch action api call - executing : "+url)

    var putReq = new XMLHttpRequest();
    putReq.open("PUT", url, false);
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
