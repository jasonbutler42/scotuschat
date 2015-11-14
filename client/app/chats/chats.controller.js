'use strict';

angular.module('scotusChatApp')

  .controller('ChatsCtrl', function (API, Nav, $scope, $rootScope, $http, $location) {
    
    API.getChats().then(function(data) {
      $scope.chats = data;
    }); 


  });
