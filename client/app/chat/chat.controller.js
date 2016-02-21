'use strict';

angular.module('scotusChatApp')
  .controller('ChatCtrl', function (API, $scope, $stateParams, $localstorage) {

  	var speakers = [];
  	var loaded = false;

    API.getSpeakers().then(function(data) {

      $localstorage.setObject('speakersCache', data);

    });  

    
    API.getChat($stateParams.chatId).then(function(data) {
      $scope.chat = data;
      loaded = true;
    }); 




  });
