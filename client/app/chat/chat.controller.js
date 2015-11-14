'use strict';

angular.module('scotusChatApp')
  .controller('ChatCtrl', function (API, $scope, $stateParams) {
    
    API.getChat($stateParams.chatId).then(function(data) {
      $scope.chat = data;
    }); 

  });
